# LLM Observability and Monitoring Tool

This repository contains a comprehensive tool for observability and monitoring of Large Language Models (LLMs).

## Project Structure

```
📁 lm_observability_and_monitoring_tool
│
├── 📁 .ebextensions          # Elastic Beanstalk configuration
├── 📁 .github                # GitHub related files
├── 📁 .git                   # Git repository data
├              # Python compiled files
│
├── 📁 core                   # Core application components
│   ├── __init__.py
│   ├── config.py             # Configuration settings
│   ├── database.py           # Database connection and models
│   ├── exceptions.py         # Custom exceptions
│   ├── logger.py             # Logging configuration
│   └  
│
├── 📁 env                    # Environment files
│
├── 📁 modules                # Application modules
│   ├── __init__.py
│   ├── services.py           # Shared services
│   ├── tests.py              # Test utilities
│   ├  
│   │
│   ├── 📁 Auth               # Authentication module
│   │   ├── __init__.py
│   │   ├── auth_routers.py   # Auth routes
│   │   ├── dependencies.py   # Auth dependencies
│   │   ├── models.py         # Auth models
│   │   ├── schemas.py        # Auth schemas
│   │   └  
│   │
│   ├── 📁 benchmark          # Benchmarking module
│   │   ├── __init__.py
│   │   ├── chunk.py          # Chunk processing
│   │   ├── file_processer.py # File processing
│   │   ├── qa_generator.py   # QA generation
│   │   ├── qa_pair.py        # QA pair models
│   │   ├── routes.py         # Benchmark routes
│   │   ├── schemas.py        # Benchmark schemas
│   │   ├── utils.py          # Benchmark utilities
│   │   └  
│   │
│   ├── 📁 hallucination_eval # Hallucination evaluation
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   └── service.py
│   │
│   ├── 📁 helpfulness_eval   # Helpfulness evaluation
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   └── service.py
│   │
│   ├── 📁 monitor            # Monitoring module
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── project_monitoror.py
│   │   └  
│   │
│   └── 📁 project_connections # Project connections
│       ├── __init__.py
│       ├── connections.py
│       ├── models.py
│       ├── project_routers.py
│       ├── schemas.py
│       └  
│
├── 📁 utils                  # Utility functions
│   ├── auth_utils.py         # Auth utilities
│   ├── connections_utils.py  # Connection utilities
│   └  
│
├── .env                      # Environment variables
├── .gitignore                # Git ignore rules
├── Procfile                  # Heroku Procfile
├── __init__.py               # Package initialization
├── application.py            # Main application entry point
├── app_database.db           # SQLite database file
├── app.log                   # Application logs
└── requirements.txt          # Python dependencies
```

## Features

- **Authentication Module**: Secure user authentication system
- **Benchmarking Tools**: Evaluate LLM performance metrics
- **Hallucination Evaluation**: Detect and measure hallucinations in LLM outputs
- **Helpfulness Evaluation**: Assess the utility and relevance of LLM responses
- **Monitoring System**: Real-time monitoring of LLM systems
- **Project Connections**: Manage connections to various LLM endpoints

## Setup and Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables in `.env` file
4. Run the application: `python application.py`

## License

[MIT License](LICENSE)