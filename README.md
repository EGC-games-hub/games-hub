# 🎮 Games Hub

<p align="center">
   <img src="app/static/img/logos/logo-dark.png" alt="Games Hub logo" width="240" />
</p>

A comprehensive web application for managing and exploring feature models in UVL format, integrated with Zenodo and Flamapy, following Open Science principles.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Development Tools](#development-tools)
- [Testing](#testing)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

Games Hub is a Flask-based web application designed to facilitate the management, exploration, and analysis of feature models. It provides a user-friendly interface for uploading, downloading, and analyzing UVL (Universal Variability Language) files, with integration to Zenodo for open science data management.

## ✨ Features

- **User Authentication & Authorization**
  - Secure signup/login system
  - Two-factor authentication (2FA) support
  - User profile management

- **Dataset Management**
  - Upload and manage datasets
  - CSV and UVL file support
  - Dataset exploration and visualization
  - Trending datasets tracking

- **Feature Model Analysis**
  - Flamapy integration for feature model operations
  - UVL validation
  - Model transformations
  - Statistical analysis

- **Zenodo Integration**
  - Direct integration with Zenodo API
  - Dataset publication
  - DOI generation
  - Metadata management

- **Recommendations System**
  - Dataset recommendations based on user preferences
  - Collaborative filtering

- **Team Collaboration**
  - Team management features
  - Shared datasets and resources

- **Webhook Support**
  - Automated deployment webhooks
  - CI/CD integration

## 🛠️ Tech Stack

### Backend
- **Flask 3.1.1** - Web framework
- **SQLAlchemy 3.1.1** - ORM
- **MariaDB** - Database
- **Alembic 1.16.4** - Database migrations
- **Flask-Login 0.6.3** - User session management
- **Flask-Mail 0.10.0** - Email support
- **Authlib 1.6.1** - OAuth support

### Analysis & Processing
- **Flamapy 2.0.1** - Feature model analysis
- **NetworkX 3.5** - Graph operations
- **Graphviz 0.21** - Visualization

### Testing & Quality
- **Pytest 8.4.1** - Testing framework
- **Coverage 7.10.1** - Code coverage
- **Flake8 7.3.0** - Linting
- **Black 25.1.0** - Code formatting
- **Selenium** - End-to-end testing

### DevOps
- **Docker & Docker Compose** - Containerization
- **Gunicorn 23.0.0** - WSGI server
- **Nginx** - Reverse proxy
- **Locust 2.37.14** - Load testing

## 📦 Prerequisites

- **Python 3.12+**
- **Docker & Docker Compose** (recommended)
- **MariaDB 10.5+** (if running without Docker)
- **Node.js** (for frontend assets, if applicable)

## 🚀 Installation

### Option 1: Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/EGC-games-hub/games-hub.git
   cd games-hub
   ```

2. **Copy environment file**
   ```bash
   cp .env.docker.example .env
   ```

3. **Build and start containers**
   ```bash
   cd docker
   docker-compose -f docker-compose.dev.yml up --build
   ```

4. **Access the application**
   - Application: http://localhost:5000
   - Selenium Hub: http://localhost:4444

### Option 2: Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/EGC-games-hub/games-hub.git
   cd games-hub
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Copy environment file**
   ```bash
   cp .env.local.example .env
   ```

5. **Setup database**
   ```bash
   # Install MariaDB and create database
   mysql -u root -p
   CREATE DATABASE uvlhubdb;
   CREATE USER 'uvlhubdb_user'@'localhost' IDENTIFIED BY 'uvlhubdb_password';
   GRANT ALL PRIVILEGES ON uvlhubdb.* TO 'uvlhubdb_user'@'localhost';
   ```

6. **Run migrations**
   ```bash
   flask db upgrade
   ```

7. **Run the application**
   ```bash
   flask run
   ```

### Option 3: Vagrant

1. **Install Vagrant and VirtualBox**

2. **Start Vagrant environment**
   ```bash
   cd vagrant
   vagrant up
   ```

## ⚙️ Configuration

### Environment Variables

Edit your `.env` file with the following configurations:

```env
# Flask Configuration
FLASK_APP_NAME="UVLHUB.IO(dev)"
FLASK_ENV=development
DOMAIN=localhost:5000

# Database Configuration
MARIADB_HOSTNAME=localhost
MARIADB_PORT=3306
MARIADB_DATABASE=uvlhubdb
MARIADB_TEST_DATABASE=uvlhubdb_test
MARIADB_USER=uvlhubdb_user
MARIADB_PASSWORD=uvlhubdb_password
MARIADB_ROOT_PASSWORD=uvlhubdb_root_password

# External Services
FAKENODO_URL=http://localhost:5001/deposit/depositions
RECOMMENDATIONS_ENABLED=1

# Add your additional configurations
```

## 🎮 Running the Application

### Development Mode

```bash
# Using Flask directly
flask run

# Using Rosemary CLI
rosemary compose env dev
rosemary update
```

### Production Mode

```bash
cd docker
docker-compose -f docker-compose.prod.yml up -d
```

### With SSL

```bash
cd docker
docker-compose -f docker-compose.prod.ssl.yml up -d
```

## 🔧 Development Tools

The project includes **Rosemary**, a powerful CLI tool for development tasks:

```bash
# Install Rosemary
pip install -e .

# Available commands
rosemary --help

# Common commands
rosemary db reset          # Reset database
rosemary db seed           # Seed database with sample data
rosemary test              # Run tests
rosemary coverage          # Run tests with coverage
rosemary linter            # Run code linting
rosemary make module       # Create new module
rosemary module list       # List all modules
rosemary route list        # List all routes
rosemary selenium          # Run Selenium tests
rosemary locust            # Run load tests
rosemary clear cache       # Clear cache
rosemary clear log         # Clear logs
rosemary info              # Show project info
```

## 🧪 Testing

### Run Unit Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Using Rosemary
rosemary test
rosemary coverage
```

### Run Selenium Tests

```bash
# Start Selenium containers first
docker-compose -f docker/docker-compose.dev.yml up selenium-hub selenium-chrome selenium-firefox

# Run Selenium tests
rosemary selenium
```

### Load Testing with Locust

```bash
rosemary locust
```


**Repository:** [EGC-games-hub/games-hub](https://github.com/EGC-games-hub/games-hub)