from setuptools import setup, find_packages

setup(
    name="venue_search_flow",
    version="0.1",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "crewai",
        "pydantic",
        "python-dotenv",
        "langchain",
        "langchain-community",
        "google-search-results",  # for SerpAPI
    ],
) 