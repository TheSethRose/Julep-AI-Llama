"""Julep Agent Management Module.

This module provides functionality for creating and managing Julep agents with custom
LLM configurations. It handles environment setup, agent creation, task execution,
and proper error handling.

Typical usage example:
    python main.py

Environment Variables:
    JULEP_API_KEY: API key for Julep service
    OPENAI_API_BASE: Base URL for OpenAI-compatible API
    OPENAI_API_KEY: API key for OpenAI (optional for some endpoints)
"""

# Standard library imports
import os
import yaml
import time
import json
from typing import Any, Dict, List, Optional, cast
from datetime import datetime
from pathlib import Path

# Third-party imports
from dotenv import load_dotenv
from julep import Julep

# Custom exception for configuration errors
class ConfigurationError(Exception):
    """Raised when there's an error in the configuration."""
    pass

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects.

    This encoder handles datetime objects by converting them to ISO format strings,
    which is necessary for JSON serialization of API responses.
    """

    def default(self, obj: Any) -> str:
        """Convert datetime objects to ISO format string.

        Args:
            obj: Object to encode

        Returns:
            str: ISO formatted datetime string if obj is datetime,
                 otherwise delegates to parent encoder
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def print_api_interaction(title: str, data: Dict[str, Any]) -> None:
    """Print API request/response data in a formatted way.

    This function helps debug API interactions by printing formatted JSON data
    with proper datetime handling.

    Args:
        title: Title of the interaction (e.g., "Creating Agent Request")
        data: Dictionary containing the data to print
    """
    print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2, cls=DateTimeEncoder))
    print("=" * (len(title) + 8))

def setup_environment() -> None:
    """Set up environment variables and validate configuration.

    This function:
    1. Loads environment variables from .env file
    2. Validates required variables are present
    3. Sets default values for optional variables
    4. Prints current configuration for debugging

    Raises:
        ConfigurationError: If required environment variables are missing
    """
    # Load variables from .env file
    load_dotenv()

    # Print current environment configuration (hiding sensitive values)
    print("\n=== Environment Configuration ===")
    env_vars = {
        "JULEP_API_KEY": bool(os.getenv("JULEP_API_KEY")),  # Show only if present
        "OPENAI_API_BASE": os.getenv("OPENAI_API_BASE", "https://api.openai.com"),
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),  # Show only if present
    }
    print(json.dumps(env_vars, indent=2))
    print("================================")

    # Check for required JULEP_API_KEY
    if not os.getenv("JULEP_API_KEY"):
        raise ConfigurationError("JULEP_API_KEY environment variable is required")

    # Set default values for optional variables
    if not os.getenv("OPENAI_API_BASE"):
        os.environ["OPENAI_API_BASE"] = "https://api.openai.com"
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "not-needed"  # Llama endpoint doesn't require key

def load_agent_config(config_path: str) -> Dict[str, Any]:
    """Load and validate agent configuration from YAML file.

    This function:
    1. Checks if the config file exists
    2. Loads and parses YAML content
    3. Prints configuration for debugging

    Args:
        config_path: Path to the agent configuration YAML file

    Returns:
        Dict containing the agent configuration

    Raises:
        ConfigurationError: If config file is missing or invalid YAML
    """
    try:
        # Check if config file exists
        config_file = Path(config_path)
        if not config_file.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")

        # Load and parse YAML
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        # Print config for debugging
        print("\n=== Agent Configuration ===")
        print(json.dumps(config, indent=2))
        print("==========================")

        return config
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML configuration: {str(e)}")

def create_agent(client: Julep, agent_config: Dict[str, Any]) -> Any:
    """Create a new Julep agent with the specified configuration.

    This function:
    1. Prepares the agent creation request
    2. Creates the agent via Julep API
    3. Prints request/response for debugging

    Args:
        client: Initialized Julep client
        agent_config: Dictionary containing agent configuration

    Returns:
        Created Agent instance

    Raises:
        Exception: If agent creation fails
    """
    # Prepare agent creation request
    agent_request = {
        "name": agent_config["name"],
        "about": "A helpful AI assistant that can answer questions and help with tasks."
    }

    # Create agent and print interaction details
    print_api_interaction("Creating Agent Request", agent_request)
    agent = client.agents.create(**agent_request)
    print_api_interaction("Agent Response", agent.__dict__)
    return agent

def create_and_execute_task(
    client: Julep,
    agent: Any,
    model_config: Dict[str, Any]
) -> Optional[str]:
    """Create and execute a chat task for the agent.

    This function:
    1. Creates a task with the specified model configuration
    2. Creates an execution for the task
    3. Monitors the execution until completion

    Args:
        client: Initialized Julep client
        agent: Agent instance to create task for
        model_config: Model configuration from agent config

    Returns:
        Optional[str]: Task execution output if successful, None otherwise
    """
    # Create task configuration with model settings
    task_yaml = f"""
name: Chat
description: Have a conversation with the user

main:
  - prompt:
      - role: system
        content: You are {{{{agent.name}}}}. {{{{agent.about}}}}
      - role: user
        content: Hello! Can you help me with something?
    unwrap: true
    model:
      name: {model_config["name"]}
      provider: {model_config["provider"]}
      settings:
        api_base: {model_config["settings"]["api_base"]}
        max_tokens: {model_config["settings"]["max_tokens"]}
        temperature: {model_config["settings"]["temperature"]}
        top_p: {model_config["settings"]["top_p"]}
"""
    # Parse YAML and add agent ID
    task_config = yaml.safe_load(task_yaml)
    task_config["agent_id"] = agent.id

    # Create task
    print_api_interaction("Creating Task Request", task_config)
    task = client.tasks.create(**task_config)
    print_api_interaction("Task Response", task.__dict__)

    # Create execution request
    execution_request = {
        "task_id": task.id,
        "input": {}
    }
    print_api_interaction("Creating Execution Request", execution_request)
    execution = client.executions.create(**execution_request)
    print_api_interaction("Execution Response", execution.__dict__)

    # Monitor execution until completion
    return monitor_execution(client, execution)

def monitor_execution(client: Julep, execution: Any) -> Optional[str]:
    """Monitor the execution of a task and handle its completion.

    This function:
    1. Polls the execution status until completion or timeout
    2. Handles different execution states (success, failure, etc.)
    3. Retrieves additional job details on failure

    Args:
        client: Initialized Julep client
        execution: Execution instance to monitor

    Returns:
        Optional[str]: Execution output if successful, None otherwise
    """
    max_retries = 30  # Maximum number of retries (30 seconds)
    retry_count = 0

    while retry_count < max_retries:
        # Get current execution status
        result = client.executions.get(execution.id)
        print(f"\nStatus: {result.status}")
        print_api_interaction("Execution Status Response", result.__dict__)

        if result.status == "succeeded":
            # Handle successful execution
            print("\n=== Final Response ===")
            print("Status:", result.status)
            print("Output:", result.output)
            print("==================")
            # Cast the output to str since we know it's a string when status is "succeeded"
            return cast(str, result.output)

        elif result.status == "failed":
            # Handle failed execution
            print("\n=== Error Response ===")
            print("Status:", result.status)
            print("Error:", result.error)
            print("Metadata:", result.metadata)
            print("Output:", result.output)
            print("Jobs:", result.__dict__.get("jobs", []))
            print("==================")

            # Try to get more information about the jobs
            jobs = result.__dict__.get("jobs", [])
            if jobs:
                for job_id in jobs:
                    try:
                        job = client.jobs.get(job_id)
                        print(f"\n=== Job {job_id} Details ===")
                        print(json.dumps(job.__dict__, indent=2, cls=DateTimeEncoder))
                        print("=" * (len(job_id) + 14))
                    except Exception as e:
                        print(f"Error getting job {job_id} details: {str(e)}")
            return None

        elif result.status == "queued" or result.status == "running":
            # Continue polling for queued or running executions
            retry_count += 1
            time.sleep(1)
            continue

        else:
            # Handle unexpected status
            print(f"\nUnexpected status: {result.status}")
            return None

    # Handle timeout
    print("\nExecution timed out after 30 seconds")
    return None

def main() -> None:
    """Main function to run the Julep agent setup and execution.

    This function:
    1. Sets up the environment
    2. Initializes the Julep client
    3. Loads agent configuration
    4. Creates and runs an agent
    5. Handles any errors that occur
    """
    try:
        # Set up environment variables
        setup_environment()

        # Initialize Julep client with API key
        client = Julep(api_key=os.getenv("JULEP_API_KEY"))

        # Load and validate agent configuration
        agent_config = load_agent_config("config/agent_config.yaml")

        # Create agent and execute task
        agent = create_agent(client, agent_config)
        output = create_and_execute_task(client, agent, agent_config["model"])

        # Handle task completion
        if output:
            print("\nTask completed successfully!")
        else:
            print("\nTask failed or timed out.")

    except ConfigurationError as e:
        # Handle configuration errors gracefully
        print(f"\nConfiguration Error: {str(e)}")
        raise SystemExit(1)
    except Exception as e:
        # Handle unexpected errors
        print(f"\nUnexpected Error: {str(e)}")
        raise  # Re-raise to see full traceback

if __name__ == "__main__":
    main()
