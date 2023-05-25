When you change your `requirements.txt` file, you'll need to rebuild your Docker image to install the new Python packages. 

Here are the steps:

1. Stop the running Docker containers with the following command:

    ```bash
    docker-compose down
    ```

2. Then rebuild and start your Docker containers:

    ```bash
    docker-compose up --build
    ```

The `--build` option tells Docker Compose to rebuild the images. If you've added new packages to your `requirements.txt` file, they will be installed during the build.

Note that Docker uses a caching mechanism during the build process, which means only the steps after the changed step will be executed. In your case, if you just changed the `requirements.txt` file, Docker will execute the `pip install --no-cache-dir -r requirements.txt` step and all subsequent steps, but will use cached layers for all previous steps.

Also, keep in mind that you may need to update the Python code to use the newly added packages, and restart the Docker container as discussed in the previous answer.