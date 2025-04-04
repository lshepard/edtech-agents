import os
import json
import glob
import logging
from typing import List, Dict, Any

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
    link: str = Field(description="A URL to the activity, if available", default="")

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
        llm = ChatOpenAI(temperature=0.7, model_name="gpt-o3-mini")
        
        # 4. Define the Tavily search tool
        tavily_tool = TavilySearch(
            max_results=5,
            description="Search the web for relevant educational resources. Use this when you need to find specific learning materials related to the student's grade level and topic."
        )
        
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=ActivityRecommendation)
        
        # 5. Define the agent prompt with structured output requirements
        system_template = """You are an expert elementary teacher. Your task is to plan an individualized 
        activity for a student based on their needs and available resources.

        First, rephrase the student's needs and available resources into a single, concise statement. Include the relevant 
        common core standards as they may help with matching.

        Next, consider the local resources provided in the context. These are pre-vetted materials 
        that may be suitable for the student's needs. Review them carefully. If any of the pre-vetted materials
        matches the subject and grade level desired, then select one of those.

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
        3. Select or recommend the best resources or activities, explaining why it's appropriate. Select 1-3 resources.
        4. For each recommendation, include a DETAILED RATIONALE that explains:
           - How this activity matches the student's grade level
           - How it specifically addresses the skills or concepts they're working on
           - Why you chose this activity over other options
           - Whether it came from local resources or web search and why
        5. You MUST format your final answer as a valid JSON array containing 1-3 activities, each with these fields: title, description, rationale, and link.

        Make sure all required fields are filled out properly and in valid JSON format.
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
        
        # 6. Create the agent
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
        
        # 8. Run the agent - we don't need to pass the variables again since they're already formatted in the system message
        response = await agent_executor.ainvoke({
            "input": "" # Empty input is required for the agent to run
        })
        
        raw_result = response.get("output", "")
        logger.info(f"Agent generated plan: {raw_result[:100]}...")
        
        # 9. Parse the structured output
        try:
            # Extract JSON from raw_result if needed (in case it contains other text)
            import re
            json_match = re.search(r'(\[[\s\S]*\])', raw_result)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find any JSON-like content
                json_match = re.search(r'({[\s\S]*})', raw_result)
                if json_match:
                    # Found a single object, wrap it in an array
                    json_str = "[" + json_match.group(1) + "]"
                else:
                    # No JSON found, treat as error
                    logger.error(f"No valid JSON found in output: {raw_result}")
                    raise ValueError("No JSON content found in the LLM response")
            
            # Log the extracted JSON for debugging
            logger.info(f"Extracted JSON: {json_str}")
            
            # Parse JSON into structured data
            recommendations_array = json.loads(json_str)
            
            # Take the first recommendation if there are multiple
            if isinstance(recommendations_array, list) and len(recommendations_array) > 0:
                # Validate each recommendation
                valid_recommendations = []
                for i, rec in enumerate(recommendations_array):
                    try:
                        # Ensure all required fields exist
                        if 'title' not in rec:
                            logger.warning(f"Recommendation {i} missing title, adding default")
                            rec['title'] = "Activity " + str(i+1)
                        
                        if 'description' not in rec:
                            logger.warning(f"Recommendation {i} missing description, adding default")
                            rec['description'] = "No description provided"
                            
                        if 'rationale' not in rec:
                            logger.warning(f"Recommendation {i} missing rationale, adding default")
                            rec['rationale'] = "Matched based on student needs"
                        
                        if 'link' not in rec:
                            rec['link'] = ""  # Default empty link is acceptable
                            
                        # Create and validate the recommendation
                        recommendation = ActivityRecommendation(**rec)
                        valid_recommendations.append(rec)
                    except Exception as e:
                        logger.error(f"Invalid recommendation {i}: {e}")
                
                if not valid_recommendations:
                    raise ValueError("No valid recommendations could be parsed")
                
                # Use the first valid recommendation as primary
                recommendation = ActivityRecommendation(**valid_recommendations[0])
                
                # Return all valid recommendations
                return {
                    "recommendations": valid_recommendations,
                    "primary_recommendation": recommendation.model_dump()
                }
            else:
                raise ValueError("Expected a JSON array with at least one recommendation")
        except Exception as e:
            logger.error(f"Error parsing structured output: {e}")
            # Fallback to returning raw text if parsing fails
            return {
                "recommendations": [{
                    "title": "Recommended Activity",
                    "description": raw_result[:1000],  # Limit the length to avoid huge responses
                    "rationale": "Generated based on your requirements",
                    "link": ""
                }],
                "primary_recommendation": {
                    "title": "Recommended Activity",
                    "description": raw_result[:1000],  # Limit the length to avoid huge responses
                    "rationale": "Generated based on your requirements",
                    "link": ""
                }
            }

    except Exception as e:
        logger.error(f"Error running agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating activity plan: {e}"
        )
