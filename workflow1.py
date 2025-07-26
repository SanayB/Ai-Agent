# import os
# import subprocess
# from crewai import Agent, Task, Crew, Process
# from langchain_community.llms import Ollama
# from crewai import LLM

# # Use Ollama instead of OpenAI
# llm = LLM(
#     llm=Ollama(model="llama3"),
#     temperature=0.3,
#     max_tokens=150
# )

# # Agents
# collector_agent = Agent(
#     role="Collector Agent",
#     goal="Fetch new CVEs and store them",
#     backstory="You gather fresh threat intelligence from NVD.",
#     allow_delegation=False,
#     verbose=True,
#     llm=llm,
# )

# analyzer_agent = Agent(
#     role="Analyzer Agent",
#     goal="Embed CVE descriptions into a vector store",
#     backstory="You convert CVE descriptions into vector embeddings in ChromaDB.",
#     allow_delegation=False,
#     verbose=True,
#     llm=llm,
# )

# summarizer_agent = Agent(
#     role="Summarizer Agent",
#     goal="Summarize latest CVEs into markdown",
#     backstory="You create readable summaries for analysts.",
#     allow_delegation=False,
#     verbose=True,
#     llm=llm,
# )

# # Tasks with subprocess
# collector_task = Task(
#     description="Run the collector script to fetch new CVEs and update cves.json.",
#     agent=collector_agent,
#     expected_output="Collector updated CVE list.",
#     async_execution=False,
#     callback=lambda _: subprocess.run(["python", "collector_agent.py"]),
# )

# analyzer_task = Task(
#     description="Run the analyzer script to embed and store new CVEs into ChromaDB.",
#     agent=analyzer_agent,
#     expected_output="Analyzer embedded new records.",
#     async_execution=False,
#     callback=lambda _: subprocess.run(["python", "analyzer_agent.py"]),
# )

# summarizer_task = Task(
#     description="Run the summarizer script to create a summary of new CVEs.",
#     agent=summarizer_agent,
#     expected_output="Markdown summary of vulnerabilities.",
#     async_execution=False,
#     callback=lambda _: subprocess.run(["python", "summarizer_agent.py"]),
# )

# # Crew
# crew = Crew(
#     agents=[collector_agent, analyzer_agent, summarizer_agent],
#     tasks=[collector_task, analyzer_task, summarizer_task],
#     llm=llm,
#     process=Process.sequential,
#     verbose=True,
# )

# if __name__ == "__main__":
#     crew.kickoff()

from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
import subprocess

# Load model (ensure it's pulled via `ollama pull llama3`)
llm = LLM(
    provider="ollama",
    model="gemma3"  # make sure you've pulled this model
   
)

collector_agent = Agent(
    role="Collector Agent",
    goal="Fetch new CVEs and store them",
    backstory="You gather fresh threat intelligence from NVD.",
    allow_delegation=False,
    verbose=True,

)

analyzer_agent = Agent(
    role="Analyzer Agent",
    goal="Embed CVE descriptions into a vector store",
    backstory="You convert CVE descriptions into vector embeddings in ChromaDB.",
    allow_delegation=False,
    verbose=True,
)

summarizer_agent = Agent(
    role="Summarizer Agent",
    goal="Summarize latest CVEs into markdown",
    backstory="You create readable summaries for analysts.",
    allow_delegation=False,
    verbose=True,
    llm=llm,
)

collector_task = Task(
    description="Run the collector script to fetch new CVEs and update cves.json.",
    agent=collector_agent,
    expected_output="Collector updated CVE list.",
    async_execution=False,
    callback=lambda _: subprocess.run(["python", "collector_agent.py"]),
)

analyzer_task = Task(
    description="Run the analyzer script to embed and store new CVEs into ChromaDB.",
    agent=analyzer_agent,
    expected_output="Analyzer embedded new records.",
    async_execution=False,
    callback=lambda _: subprocess.run(["python", "analyzer_agent.py"]),
)

summarizer_task = Task(
    description="Run the summarizer script to create a summary of new CVEs.",
    agent=summarizer_agent,
    expected_output="Markdown summary of vulnerabilities.",
    async_execution=False,
    callback=lambda _: subprocess.run(["python", "summarizer_agent.py"]),
)

crew = Crew(
    agents=[collector_agent, analyzer_agent, summarizer_agent],
    tasks=[collector_task, analyzer_task, summarizer_task],
    llm=llm,
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    crew.kickoff()
