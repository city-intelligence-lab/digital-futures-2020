# DigitalFUTURES 2020

The official repo for the _Artificial Intelligence for Resilient Urban Planning_ workshop by the City Intelligence Lab. The workshop was conducted from the 28th of June to the 3rd of July and was streamed live to our [YouTube channel](https://www.youtube.com/playlist?list=PLmEjjLGXj_meytRKhNccd_m5z6UUpsqM8). This repo contains all of the workshop slides and files.

## Software Requirements

### Python

Download and install Anaconda ([https://www.anaconda.com/distribution/](https://www.anaconda.com/distribution/), python 3).

If you already have Python installed on your system, please double check that it is ≥3.6 and that you can set up either *virtualenvs* or *pipenvs*.

#### `/mlgh-pix2pix`

1. Open anaconda prompt and create a new environment named "pix2pix" using the following command (more info here: [https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)):

    ```bash
    conda create --name pix2pix python=3.7
    ```

2. Activate that conda environment:

    ```bash
    activate pix2pix
    ```

3. Install the required packages (copy/paste commands):

    ```bash
    conda install -c pytorch pytorch torchvision cudatoolkit=10.0
    ```

    ```bash
    conda install -c conda-forge altair vega_datasets notebook vega h5py hdf5 imageio matplotlib seaborn pandas numpy networkx graphviz category_encoders feather-format scikit-learn scikit-image dominate visdom moviepy jsonpatch
    ```

    ```bash
    conda install scipy==1.1.0
    ```

    ```bash
    conda install Pillow
    ```

    ```bash
    pip install opencv-contrib-python
    ```

#### `/mlgh-dqn`

1. Open anaconda prompt and create a new environment named "dqn" and activate it:

    ```bash
    conda create --name dqn python=3.6
    ```

    ```bash
    activate dqn
    ```

2. Install the required package:

    ```bash
    conda install tensorflow
    ```

### Grasshopper

Download the following plugins from Food4Rhino. If you already have them installed, make sure they are the latest version!

- GH_CPython ([https://www.food4rhino.com/app/ghcpython](https://www.food4rhino.com/app/ghcpython))
    - In some case you might need to adjust paths to your python installation in the GH component. See our Slack channel for more information on how to do that.
- Hoopsnake ([https://www.food4rhino.com/app/hoopsnake](https://www.food4rhino.com/app/hoopsnake))
- Aviary (**Make sure** to use the “Pre Release Download (1.00.0011)” version from **2018**, [https://www.food4rhino.com/app/aviary](https://www.food4rhino.com/app/aviary))
- Human ([https://www.food4rhino.com/app/human](https://www.food4rhino.com/app/human))
- TT Toolbox ([https://www.food4rhino.com/app/tt-toolbox](https://www.food4rhino.com/app/tt-toolbox))
- DeCodingSpaces (optional, [https://toolbox.decodingspaces.net/download-decodingspaces-toolbox/](https://toolbox.decodingspaces.net/download-decodingspaces-toolbox/) )
- HumanUI (optional, [https://www.food4rhino.com/app/human-ui](https://www.food4rhino.com/app/human-ui))

### Mapillary

#### `/colab-notebooks/streetview-images.ipynb`

1. If you haven't already, sign up for a Mapillary account [here](https://www.mapillary.com/app/?signup=true).
2. Create a client ID to access the API by visiting the developers [dashboard](https://www.mapillary.com/dashboard/developers) and clicking "Register Application" on the top right of the screen.
3. Fill in the "Register an Application" form making sure to switch the "private:read" toggle in the "Allow this application to" section. Note that the callback URL will act as the IP where you'll be making requests from. 
4. Retrieve your token (used for making requests) by going to:

    `https://www.mapillary.com/connect?scope=private:read&client_id=<client_id>&redirect_uri=<callback_url>&state=return&response_type=token`

    replacing `<client_id>` and `<callback_url>` with these values found in the [dashboard](https://www.mapillary.com/dashboard/developers). 

5. If successful, you should be redirected to your `callback_url`, but with a different URL in the address bar. At the end of your `callback_url` you should see `?token_type=bearer&access_token=` followed by a giant string. This is your access token. Copy everything between `access_token=` and `&expires_in=never&state=return`, and save it somewhere.
