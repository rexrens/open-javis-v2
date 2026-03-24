from agno.agent import Agent, RunOutput
from agno.models.deepseek import DeepSeek
from agno.tools.coding import CodingTools
import sys

def main(message:str):
    agent = Agent(
        model=DeepSeek(id="deepseek-reasoner", api_key="sk-e5e13f36e6744fea8f95b2fe067649de"),
        # tools=[CodingTools()],
        # add_history_to_context=True,
        # markdown=True,
    )

    output:RunOutput = agent.run(message)

    print(output.reasoning_content)
    print('-------------------')
    print(output.content)
 

if __name__ == "__main__":
    main(sys.argv[1])
