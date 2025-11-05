"""
Setup script for the TradingAgents package.
"""

from setuptools import setup, find_packages

setup(
    name="tradingagents",
    version="0.1.0",
    description="Multi-Agents LLM Financial Trading Framework",
    author="TradingAgents Team",
    author_email="yijia.xiao@cs.ucla.edu",
    url="https://github.com/TauricResearch",
    packages=find_packages(),
    install_requires=[
        "chromadb>=1.0.12",
        "fastapi>=0.110.0",
        "langchain-openai>=0.3.23",
        "langgraph>=0.4.8",
        "pandas>=2.3.0",
        "python-multipart>=0.0.6",
        "questionary>=2.1.0",
        "requests>=2.32.4",
        "rich>=14.0.0",
        "stockstats>=0.6.5",
        "tqdm>=4.67.1",
        "typing-extensions>=4.14.0",
        "uvicorn[standard]>=0.29.0",
        "websockets>=12.0",
        "yfinance>=0.2.63",
    ],
    extras_require={
        "data-feeds": [
            "akshare>=1.16.98",
            "backtrader>=1.9.78.123",
            "eodhd>=1.0.32",
            "feedparser>=6.0.11",
            "finnhub-python>=2.4.23",
            "parsel>=1.10.0",
            "praw>=7.8.1",
            "tushare>=1.4.21",
        ],
        "llm-providers": [
            "langchain-anthropic>=0.3.15",
            "langchain-experimental>=0.3.4",
            "langchain-google-genai>=2.1.5",
        ],
        "ops": [
            "chainlit>=2.5.5",
            "grip>=4.6.2",
            "redis>=6.2.0",
        ],
    },
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "tradingagents=cli.main:app",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Trading Industry",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
)
