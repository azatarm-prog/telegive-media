# Telegive Media Management Service

This is the Media Management Service for the Telegive platform. It is responsible for handling all media uploads, processing, storage, and cleanup.

## Features

- **File Upload:** Securely upload image and video files.
- **File Validation:** Validate files based on type, size, and format.
- **Security Scanning:** Scan files for potential security threats.
- **Metadata Extraction:** Extract metadata from images and videos.
- **File Storage:** Store files in a structured and organized manner.
- **File Cleanup:** Automatically clean up files after giveaways are published.
- **API Endpoints:** A comprehensive set of API endpoints for managing media.
- **Scheduled Tasks:** Background tasks for cleanup and validation.
- **Authentication:** Secure endpoints with JWT-based authentication.
- **Service Integration:** Integrate with other Telegive services.

## Tech Stack

- **Backend:** Flask
- **Database:** PostgreSQL
- **Task Scheduling:** APScheduler
- **Containerization:** Docker
- **Deployment:** Railway

## API Documentation

### Health Check

- `GET /health`: Basic health check.
- `GET /health/detailed`: Detailed health check with service dependencies.

### Upload

- `POST /api/media/upload`: Upload a media file.
- `GET /api/media/upload/status`: Get upload configuration and status.

### Media Management

- `GET /api/media/`: Media service index.
- `GET /api/media/<file_id>`: Get file information.
- `GET /api/media/<file_id>/download`: Download a file.
- `DELETE /api/media/<file_id>`: Delete a file.
- `PUT /api/media/<file_id>/associate`: Associate a file with a giveaway.
- `POST /api/media/cleanup/<giveaway_id>`: Cleanup files for a giveaway.
- `GET /api/media/account/<account_id>`: Get all files for an account.
- `POST /api/media/validate/<file_id>`: Validate a file.

## Setup and Deployment

### Local Development

1.  Clone the repository.
2.  Create a virtual environment: `python -m venv venv`
3.  Activate the virtual environment: `source venv/bin/activate`
4.  Install dependencies: `pip install -r requirements.txt`
5.  Set up the database and environment variables (see `.env.example`).
6.  Run the application: `flask run`

### Docker

1.  Build the Docker image: `docker build -t telegive-media .`
2.  Run the Docker container: `docker run -p 8005:8005 telegive-media`

### Railway

The service is configured for deployment on Railway using the `Procfile`.

## Testing

To run the tests, use the following command:

```bash
pytest
```

This will run all unit, integration, and end-to-end tests and generate a coverage report.


