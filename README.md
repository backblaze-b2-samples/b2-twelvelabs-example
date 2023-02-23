# Backblaze B2 + bunny.net + TransloadIt Video Sharing Example

'CatTube' is a simple video sharing website comprising: 

* A web app implemented with [Django](https://www.djangoproject.com) and JavaScript.
* Video uploading with [Uppy](https://uppy.io) and processing at [TransloadIt](https://transloadit.com/).
* Cloud object storage at [Backblaze B2](https://www.backblaze.com/b2/cloud-storage.html).
* Content distribution via [bunny.net](bunny.net).

## User Experience

* Users upload videos from their browser to TransloadIt via the Uppy widget on the web app's 'Upload Video' page.

* Once the video is uploaded, a JavaScript front end in the browser polls an API at the web app until the transcoded version is available.

* TransloadIt transforms the video file according to a preconfigured template and saves the following set of assets to a private bucket in Backblaze B2:

  * The original video uploaded by the user
  * An intermediate, resized version of the video
  * The final resized, watermarked video for sharing
  * A thumbnail image taken from the watermarked video

* Once processing is complete, TransloadIt POSTs a JSON notification back to the web app containing full details of the 'assembly' process.

* The web app updates the video's database record with the name of the transcoded file.

* The next call from the JavaScript front end will return with the name of the transcoded video, signalling that the transcoding operation is complete. The browser shows the transcoded video, ready for viewing.

## Prerequisites

* An internet-accessible host
* [Python 3.9.2](https://www.python.org/downloads/release/python-392/) (other Python versions _may_ work) and `pip`
* A Backblaze account. [Sign up here](https://www.backblaze.com/b2/sign-up.html?referrer=nopref).
* A bunny.net account. [Sign up here](https://panel.bunny.net/user/register/).
* A TransloadIt account. [Sign up here](https://transloadit.com/c/signup/).

## Backblaze B2

TBD - expand this!

Create a private bucket, and two application keys to access that bucket: one write-only (for use by TransloadIt) and one read-only (for use by bunny.net). Make careful note of each key - you will not be able to retrieve them after navigating away from the page!

## bunny.net

TBD

## TransloadIt

Click **Credentials** in the navigation menu on the left, then, under **Third-party Credentials** click **Add new Credential**. Select **Backblaze** as the service, name the key `backblaze-write-only`, and paste in the Backblaze B2 Bucket name, Application Key ID and Application Key. Click **Save**.

Now click **Templates** in the left nav menu, then **New Template**. Click **Blank** to create an empty template. Give the template a suitable name and paste in the [assembly instructions](assembly-instructions.json). Feel free to replace the `watermark_url` and otherwise customize the template! Finally, click **Create Template** and copy the template id displayed at the top of the page.

## Web Application

### Installation

Clone this repository onto the host, `cd` into the local repository directory, then use `pip install` to install dependencies for the components as required:

```bash
git clone git@github.com:backblaze-b2-samples/b2-transloadit-example.git
cd b2-transloadit-example
pip install -r requirements.txt
```

### Configuration

TBD - rework configuration so that static web assets are in bunny.

Create a `.env` file in the project directory or set environment variables with your configuration:

```bash
AWS_S3_REGION_NAME="<for example: us-west-001>"
AWS_ACCESS_KEY_ID="<your B2 application key ID>"
AWS_SECRET_ACCESS_KEY="<your B2 application key>"
AWS_PRIVATE_BUCKET_NAME="<your private B2 bucket, for uploaded videos>"
AWS_STORAGE_BUCKET_NAME="<your public B2 bucket, for static web assets>"
```

Edit `cattube/settings.py` and add the domain name of your application server to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`. For example, if you were running the sample at `videos.example.com` you would use

```python
ALLOWED_HOSTS = ['videos.example.com']

CSRF_TRUSTED_ORIGINS = ['https://videos.example.com']
```

_Note that `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` are lists of strings - the square brackets are required._

Run the usual commands to initialize a Django application:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
```

### Run the Web App

To start the development server:

```bash
python manage.py runserver
```

You may provide the runserver command with the interface and port to which the web app should bind. For example, to
listen on the standard HTTP port on all interfaces, you would use:

```bash
python manage.py runserver 0.0.0.0:80
```

## Caveats

Note that this is an example system! To run a similar system in production, you would need to make several changes,
including running the app from a WSGI server such as [Green Unicorn](http://gunicorn.org/)
  or [Apache Web Server](https://httpd.apache.org) with [`mod_wsgi`](https://github.com/GrahamDumpleton/mod_wsgi).

Feel free to fork this repository and submit a pull request if you make an interesting change!

_The web application is based on the [Backblaze B2 Video Sharing Example](https://github.com/backblaze-b2-samples/b2-video-sharing-example), which in turn was originally forked from the 
excellent [simple-s3-setup](https://github.com/sibtc/simple-s3-setup) by [sibtc](https://github.com/sibtc/)_.
