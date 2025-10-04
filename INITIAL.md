## FEATURE

I am building an SRE agent that will be used to troubleshoot and resolve issues in our infrastructure and do finops. There will be coordinator agent that will coordinate and pass to other agents like finops agent that has access to aws cloudwatch mcp tools. In this iteration, i want to build finops agent that will query cost explorer mcp tools and give me the cost of the resources.

## EXAMPLES
Multi agent structure on strands framework.
```
# Researcher Agent with web capabilities
researcher_agent = Agent(
    system_prompt=(
        "You are a Researcher Agent that gathers information from the web. "
        "1. Determine if the input is a research query or factual claim "
        "2. Use your research tools (http_request, retrieve) to find relevant information "
        "3. Include source URLs and keep findings under 500 words"
    ),
    callback_handler=None,
    tools=[http_request]
)

# Analyst Agent for verification and insight extraction
analyst_agent = Agent(
    callback_handler=None,
    system_prompt=(
        "You are an Analyst Agent that verifies information. "
        "1. For factual claims: Rate accuracy from 1-5 and correct if needed "
        "2. For research queries: Identify 3-5 key insights "
        "3. Evaluate source reliability and keep analysis under 400 words"
    ),
)

# Writer Agent for final report creation
writer_agent = Agent(
    system_prompt=(
        "You are a Writer Agent that creates clear reports. "
        "1. For fact-checks: State whether claims are true or false "
        "2. For research: Present key insights in a logical structure "
        "3. Keep reports under 500 words with brief source mentions"
    )
)
```

### Workflow Orchestration
```
def run_research_workflow(user_input):
    # Step 1: Researcher Agent gathers web information
    researcher_response = researcher_agent(
        f"Research: '{user_input}'. Use your available tools to gather information from reliable sources.",
    )
    research_findings = str(researcher_response)

    # Step 2: Analyst Agent verifies facts
    analyst_response = analyst_agent(
        f"Analyze these findings about '{user_input}':\n\n{research_findings}",
    )
    analysis = str(analyst_response)

    # Step 3: Writer Agent creates report
    final_report = writer_agent(
        f"Create a report on '{user_input}' based on this analysis:\n\n{analysis}"
    )

    return final_report
```





## DOCUMENTATION

-[Multi Agent Example](https://strandsagents.com/latest/documentation/docs/examples/python/multi_agent_example/multi_agent_example/)
-[Agent Workflows Example](https://strandsagents.com/latest/documentation/docs/examples/python/agents_workflows/)

## OTHER CONSIDERATIONS

- Make sure to use `strands-agents` mcp server to get the documentation and examples for strands framework and awslabs.aws-documentation-mcp-server for aws documentation.
- Make sure functionality both services are working together.
