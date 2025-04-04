import os
import json
import glob
import logging
from typing import List, Dict, Any, Optional

from fastapi import HTTPException, status # Import HTTPException and status

# Langchain imports
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# New imports for Tavily and Agent
from langchain_tavily import TavilySearch
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

logger = logging.getLogger("server")

CONTEXT_DIR = "../../context" # Adjusted path relative to planner.py

# Define the structured output model
class ActivityRecommendation(BaseModel):
    """Structured output for an activity recommendation."""
    title: str = Field(description="The title or name of the recommended activity")
    description: str = Field(description="A brief description of the activity")
    rationale: str = Field(description="Why this activity is appropriate for the student")
    link: Optional[str] = Field(description="A URL to the activity, if available")

class ActivityRecommendationList(BaseModel):
    """List of activity recommendations"""
    recommendations: List[ActivityRecommendation] = Field(
        description="List of activity recommendations containing 1-3 items"
    )

def load_context_files(directory: str) -> List[Dict[str, Any]]:
    """Loads all JSON files from the specified directory."""
    context_data = []
    # Adjust path relative to this file's location (app/llm)
    abs_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), directory))
    json_files = glob.glob(os.path.join(abs_directory, "*.json"))
    if not json_files:
        logger.warning(f"No JSON context files found in {abs_directory}")
        return []

    for file_path in json_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                context_data.append(data)
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from file: {file_path}")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
    return context_data

async def generate_activity_plan(grade_level: str, working_on: str) -> Dict[str, Any]:
    """Generates an activity plan using LLM, context, and Tavily search.
    
    Returns a dictionary with:
      - recommendations: List of all recommended activities
      - primary_recommendation: The first recommendation as a structured object
    """
    logger.info(f"Generating plan for: Grade={grade_level}, WorkingOn='{working_on}'")

    # 1. Load context data
    context_data = load_context_files(CONTEXT_DIR)
    if not context_data:
        logger.error(f"Essential context data not found in {CONTEXT_DIR}. Cannot generate plan.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: Missing context data for planning."
        )
    
    # Properly escape the JSON context data to prevent template variable conflicts
    context_str = json.dumps(context_data, indent=2)
    # Replace curly braces with double curly braces to escape them in the template
    context_str = context_str.replace('{', '{{').replace('}', '}}')
    
    # Also escape any potential curly braces in the user inputs
    safe_grade_level = grade_level.replace('{', '{{').replace('}', '}}')
    safe_working_on = working_on.replace('{', '{{').replace('}', '}}')

    # 2. Check if required API Keys are set
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: Missing OpenAI API key."
        )
    
    if not os.getenv("TAVILY_API_KEY"):
        logger.error("TAVILY_API_KEY environment variable not set.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: Missing Tavily API key."
        )

    try:
        # 3. Initialize the LLM
        llm = ChatOpenAI(model_name="gpt-4o")
        
        # 4. Define the Tavily search tool
        tavily_tool = TavilySearch(
            max_results=5,
            description="Search the web for relevant educational resources. Use this when you need to find specific learning materials related to the student's grade level and topic."
        )
        
        # 5. Define the system message for the agent
        system_template = """You are an expert elementary teacher. Your task is to plan an individualized 
        activity for a student based on their needs and available resources.

        First, rephrase the student's needs and available resources into a single, concise statement. Include the relevant 
        common core standards as they may help with matching.

        Next, consider the local resources provided in the context. These are pre-vetted materials 
        that may be suitable for the student's needs. Review them carefully. Prefer materials that match grade level but 
        if any of the pre-vetted materials
        matches the subject desired (even if a different grade level), then select one of those.

        ONLY FALL BACK TO SEARCH if there are no local resources that match.
        In that case, then you can search the web for reliable, high quality educational games and activities that teach the specific skill.

        The student's information is:
        Grade Level: {grade_level}
        Working on: {working_on}

        Available local resources:
        {context}

        Steps:
        1. Review the student's information and the available local resources.
        2. If necessary, search for appropriate educational resources that match the student's grade level and topic. Search for "open educational resources" and look for links that can be utilized without any issues.
        3. Select or recommend the best resources or activities, explaining why it's appropriate. Choose between 1-3 resources.
        4. For each recommendation, include a DETAILED RATIONALE that explains:
           - How this activity matches the student's grade level
           - How it specifically addresses the skills or concepts they're working on
           - Why you chose this activity over other options
           - Whether it came from local resources or web search and why
        
        You MUST structure your output as a list of activity recommendations, each containing:
        - title: The name of the activity (required)
        - description: A detailed description of the activity (required)
        - rationale: Why this activity is appropriate for the student (required)
        - link: URL to the activity (optional, use an empty string "" if not available)
        """
        
        # Format the system message with the actual values
        formatted_system_message = system_template.format(
            grade_level=grade_level,
            working_on=working_on,
            context=context_str
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", formatted_system_message),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 6. Create the agent with structured output
        agent = create_openai_functions_agent(
            llm=llm, 
            tools=[tavily_tool], 
            prompt=prompt
        )
        
        # 7. Create the agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=[tavily_tool],
            verbose=True,
            handle_parsing_errors=True,
        )
        
        # 9. Run the agent to gather information and process
        response = await agent_executor.ainvoke({
            "input": "" # Empty input is required for the agent to run
        })
        
        raw_result = response.get("output", "")
        logger.info(f"Agent generated plan: {raw_result[:100]}...")
        
        # 10. Process the raw output into structured format
        try:
            # First, try direct JSON parsing if the output seems to be in JSON format
            try:
                import re
                json_match = re.search(r'(\[[\s\S]*\])', raw_result)
                if json_match:
                    json_str = json_match.group(1)
                    # Try to parse as direct JSON array of recommendations
                    recommendations_array = json.loads(json_str)
                    
                    # Validate and convert to our expected format
                    valid_recommendations = []
                    for rec in recommendations_array:
                        # Ensure all required fields exist
                        if 'title' not in rec:
                            rec['title'] = "Recommended Activity"
                        if 'description' not in rec:
                            rec['description'] = "No description provided"
                        if 'rationale' not in rec:
                            rec['rationale'] = "Matched based on student needs"
                        if 'link' not in rec or rec['link'] is None:
                            rec['link'] = ""
                        
                        # Add to valid recommendations
                        valid_recommendations.append(rec)
                    
                    if valid_recommendations:
                        return {
                            "recommendations": valid_recommendations,
                            "primary_recommendation": valid_recommendations[0]
                        }
            except Exception as json_error:
                logger.info(f"Direct JSON parsing failed, trying with LLM structured output: {json_error}")
                
            # If direct parsing fails, use LLM with structured output
            # Try with tool calling approach
            llm_for_structure = ChatOpenAI(model_name="gpt-4o")
            
            # Create a function-calling format that OpenAI supports
            structured_llm = llm_for_structure.bind_tools(
                [ActivityRecommendationList], 
                tool_choice={"type": "function", "function": {"name": "ActivityRecommendationList"}}
            )
            
            # Let the LLM structure the output
            structured_result = structured_llm.invoke(
                f"""Extract activity recommendations from this text and format them according to the required structure:
                
                {raw_result}
                
                The output should contain 1-3 activity recommendations, each with title, description, rationale, and optional link fields.
                """
            )
            
            # Extract the tool call from the response
            if hasattr(structured_result, 'tool_calls') and structured_result.tool_calls:
                tool_call = structured_result.tool_calls[0]
                recommendations_list = tool_call.get('args', {}).get('recommendations', [])
                
                # Process recommendations to ensure proper format
                valid_recommendations = []
                for rec in recommendations_list:
                    # Ensure all fields exist and None values are converted to empty strings
                    if rec.get('link') is None:
                        rec['link'] = ""
                    valid_recommendations.append(rec)
                
                if valid_recommendations:
                    return {
                        "recommendations": valid_recommendations,
                        "primary_recommendation": valid_recommendations[0]
                    }
                else:
                    raise ValueError("No valid recommendations found in structured output")
            else:
                raise ValueError("No tool calls found in structured output")
            
        except Exception as e:
            logger.error(f"Error processing structured output: {e}")
            # Final fallback - create a simple recommendation from the raw text
            try:
                # Basic fallback to ensure we return something
                simple_recommendation = {
                    "title": "Recommended Activity",
                    "description": raw_result[:500] + "..." if len(raw_result) > 500 else raw_result,
                    "rationale": "Generated based on student requirements",
                    "link": ""
                }
                
                return {
                    "recommendations": [simple_recommendation],
                    "primary_recommendation": simple_recommendation
                }
            except Exception as final_error:
                logger.error(f"Final fallback error: {final_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate properly structured activity recommendations"
                )

    except Exception as e:
        logger.error(f"Error running agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating activity plan: {e}"
        )
