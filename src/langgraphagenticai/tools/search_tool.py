from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import ToolNode

def get_tools():
    """
    return the list of tool to be used in the chatbpat
    """
    tools=[TavilySearchResults(max_results=2)]
    return tools

def create_tool_node(tools):
    """
    Docstring for create_tool_node
    create and returns a tool node for the graph
    """
    return ToolNode(tools=tools)