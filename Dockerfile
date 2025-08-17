# Use the official Python image as the base image
FROM python:3.13.3-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Install PostgreSQL client libraries
RUN apt-get update && apt-get install -y libpq-dev gcc postgresql-client

# Copy the requirements file to the working directory
COPY requirements.txt /app/

# Install dependencies using pip
RUN pip install -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . /app/

# Expose the port your Django application runs on
EXPOSE 8000
EXPOSE 8001

# Define the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
COPY asgi-entrypoint.sh /usr/local/bin/asgi-entrypoint.sh
RUN chmod +x /usr/local/bin/asgi-entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]

# Run the Django application
CMD ["gunicorn", "pms.wsgi:application", "--bind", "0.0.0.0:8000"]
