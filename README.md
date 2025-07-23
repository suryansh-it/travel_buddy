# tripbozo - Travel App Recommendation Platform


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Django](https://img.shields.io/badge/Django-4.x-green.svg)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)

tripbozo is a comprehensive travel companion platform that provides curated app bundles for travelers based on their destination country. The platform consists of a robust Django backend API and a modern frontend interface.

## 🌟 Features

- **Country-Specific App Recommendations**: Get curated lists of essential travel apps based on your destination
- **QR Code Generation**: Share app bundles easily through QR codes
- **Session Management**: Redis-backed sessions with 24-hour expiry
- **Analytics Dashboard**: Track usage statistics and user engagement
- **RESTful API**: Fully documented API with OpenAPI/Swagger support
- **Authentication**: JWT-based user authentication system
- **Background Tasks**: Celery integration for asynchronous processing

## 🏗️ Architecture

### Backend Components

| Module                    | Purpose                                                |
| ------------------------- | ------------------------------------------------------ |
| `auth_app`               | JWT-based authentication & user management            |
| `country`                | Country data management and utilities                 |
| `personalized_list`      | Core app recommendation and bundle generation         |
| `scrapper`               | Data scraping utilities for app information          |
| `services`               | External service integrations                         |
| `healthz`                | Health check endpoints                               |
| `homepage`               | Landing page and general content                      |
| `itinerary`              | Travel itinerary management                           |

## 🚀 API Endpoints

| Method | Path                          | Description                         |
| ------ | ----------------------------- | ----------------------------------- |
| GET    | `/api/countries/`             | List supported countries            |
| GET    | `/api/bundles/?country=IN`    | Fetch curated app bundle            |
| POST   | `/api/bundles/`               | Create new bundle (returns session) |
| GET    | `/api/bundles/{id}/qr/`       | Retrieve QR code image              |
| POST   | `/api/auth/login/`            | Obtain JWT tokens                   |
| GET    | `/api/analytics/usage/`       | Fetch usage statistics              |

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8+
- Redis Server
- PostgreSQL/MySQL (optional, SQLite for development)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/suryansh-it/travel_buddy.git
cd travel_buddy

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend/django_admin
pip install -r requirements.txt

# Environment setup
cp .env.example .env
# Edit .env with your configuration

# Database migration
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### Frontend Setup

The frontend repository is available at: [tripbozo Frontend](https://github.com/suryansh-it/tripbozofrontend)

```bash
# Clone frontend repository
git clone https://github.com/suryansh-it/tripbozofrontend.git
cd tripbozofrontend

# Follow frontend-specific setup instructions
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `backend/django_admin/` directory:

```env
# Database
DATABASE_URL=your_database_url

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your_secret_key
DEBUG=True

# External APIs
# Add your API keys here
```

### Redis Setup

```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Start Redis server
redis-server

# Or using Docker
docker run -d -p 6379:6379 redis:alpine
```

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test auth_app
python manage.py test country
python manage.py test personalized_list

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

## 📊 Usage Examples

### Get Country List

```bash
curl -X GET "http://localhost:8000/api/countries/" \
  -H "Content-Type: application/json"
```

### Create App Bundle

```bash
curl -X POST "http://localhost:8000/api/bundles/" \
  -H "Content-Type: application/json" \
  -d '{"country": "IN", "preferences": ["navigation", "translation"]}'
```

### Generate QR Code

```bash
curl -X GET "http://localhost:8000/api/bundles/{bundle_id}/qr/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Getting Started

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Run tests**
   ```bash
   python manage.py test
   ```
5. **Commit your changes**
   ```bash
   git commit -m 'Add some amazing feature'
   ```
6. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guidelines
- Write meaningful commit messages
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

### Code Style

```bash
# Install development dependencies
pip install black flake8 isort

# Format code
black .

# Sort imports
isort .

# Lint code
flake8 .
```

## 📁 Project Structure

```
travel_buddy/
├── backend/
│   └── django_admin/
│       ├── manage.py
│       ├── requirements.txt
│       ├── auth_app/          # User authentication
│       ├── country/           # Country data management
│       ├── personalized_list/ # App recommendations
│       ├── scrapper/          # Data scraping
│       ├── services/          # External integrations
│       ├── healthz/           # Health checks
│       ├── homepage/          # Landing page
│       └── itinerary/         # Travel planning
├── LICENSE
└── README.md
```

## 🐛 Issue Reporting

Found a bug? Have a suggestion? Please create an issue:

1. Check existing issues first
2. Use the issue template
3. Provide detailed description
4. Include steps to reproduce
5. Add relevant labels

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌐 Related Projects

- **Frontend**: [tripbozo Frontend](https://github.com/suryansh-it/tripbozofrontend)
- **Mobile App**: Coming soon...

## 👥 Team

- **Suryansh** - Project Lead & Backend Developer
- **Nikhil** - Frontend Developer
- **Harsh** - Frontend Developer
- **Ankit** - Backend Developer

## 🙏 Acknowledgments

- Django and Django REST Framework communities
- Contributors and testers
- Open source libraries used in this project

## 📞 Support

- Create an [issue](https://github.com/suryansh-it/travel_buddy/issues) for bug reports
- Start a [discussion](https://github.com/suryansh-it/travel_buddy/discussions) for questions
- Contact the maintainers for urgent matters

---

Made with ❤️ for travelers worldwide
=======

