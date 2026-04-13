from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_news,
    get_global_news,
)
from tradingagents.dataflows.config import get_config


def create_india_macro_analyst(llm):
    def india_macro_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_news,
            get_global_news,
        ]

        system_message = (
            """You are an India Macro Analyst specializing in the Indian financial markets. Your task is to analyze the macroeconomic environment in India and its impact on the stock being analyzed. Focus specifically on:

1. **RBI Monetary Policy**: Current repo rate, CRR, SLR, recent policy changes, forward guidance, and impact on liquidity and borrowing costs.
2. **FII/DII Flows**: Foreign Institutional Investor (FII) and Domestic Institutional Investor (DII) buying/selling trends. Are FIIs pulling out or investing? Are DIIs providing support?
3. **Currency & Commodities**: INR/USD exchange rate trends, crude oil prices (India imports ~85% of oil), gold prices, and their impact on inflation and corporate margins.
4. **Government Policy**: Recent Union Budget announcements, PLI (Production Linked Incentive) schemes, divestment plans, GST collections, fiscal deficit targets.
5. **India GDP & Inflation**: Latest GDP growth data, CPI/WPI inflation numbers, and their implications for markets.
6. **Sectoral Impact**: How the above macro factors specifically affect the sector of the company being analyzed (e.g., IT sector benefits from weak INR, banks benefit from rate cuts, FMCG affected by rural demand).
7. **Global Spillovers**: How US Fed policy, China slowdown, or geopolitical events are impacting Indian markets specifically.

Search for recent Indian market news, RBI announcements, and macro data. Write a comprehensive report with specific data points, dates, and actionable trading implications. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."""
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "india_macro_report": report,
        }

    return india_macro_analyst_node
