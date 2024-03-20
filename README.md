# Flask VIN Decoder App

This is a Flask app that decodes VIN numbers using Selenium and a headless Chrome browser. It is designed to be deployed as a Docker container on Azure.

## Requirements

- Docker
- Azure account
- Azure CLI (optional)

## Local Setup

1. Clone the repository:

git clone https://github.com/your-username/your-repository.git


2. Build the Docker image:

docker build -t vin-decoder-app:latest .


4. Access the app at `http://localhost:5000`.


## Deployment to Azure

1. Push the Docker image to Azure Container Registry (ACR):

az acr login --name yourRegistryName
docker tag vin-decoder-app:latest yourRegistryName.azurecr.io/vin-decoder-app:latest
docker push yourRegistryName.azurecr.io/vin-decoder-app:latest



2. Deploy the image to Azure App Service or Azure Container Instances:
- Create a new Web App for Containers or a new container instance in the Azure Portal.
- Use the image from ACR as the source.
- Set any necessary environment variables and configure the port settings.

3. Access your app using the URL provided by Azure, or attach your own.


