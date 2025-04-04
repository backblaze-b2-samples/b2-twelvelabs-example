# Backblaze B2 + Twelve Labs Media Asset Management Example

This is a simple media asset management app comprising: 

* A web app with a [Django](https://www.djangoproject.com) back end and JavaScript front end.
* Background tasks managed by [Huey](https://huey.readthedocs.io/en/latest/).
* Video uploading with [Uppy](https://uppy.io) and processing at [TransloadIt](https://transloadit.com/).
* Cloud object storage at [Backblaze B2](https://www.backblaze.com/b2/cloud-storage.html).
* Video understanding by [Twelve Labs](https://www.twelvelabs.io/)

The app shows how to:

* Submit videos stored in Backblaze B2 for indexing by Twelve Labs.
* Perform deep semantic search on the video index across both visual and audio modalities.
* Display search results, allowing the user to drill down and view segments of video returned by the search. 

## User Experience

<figure>
  <img src="screenshots/list-page.png" alt="CatTube index page" width="1024"/>
  <figcaption>Index Page</figcaption>
</figure>

### Uploading Videos

* Users upload videos from their browser to Backblaze B2 via TransloadIt's Uppy widget on the web app's 'Upload Video' page.

* Once the video is uploaded, a JavaScript front end in the browser polls an API at the web app, monitoring its status.

* A Huey task polls TransloadIt until the upload is complete, at which point it updates the video's database record with the name of the uploaded file.

* The next call from the JavaScript front end will return with the name of the uploaded video, signalling that the upload operation is complete. The browser shows the uploaded video with a white noise thumbnail, indicating that it is stored in Backblaze B2, but not yet indexed by Twelve Labs.

### Indexing Videos

* A user selects one or more videos in the web app, and hits the **Index** button.

* The JavaScript front end sends the list of videos to an API in the web app.

* The web app's index API starts a Huey task that creates a Twelve Labs index task for each video, then polls for the status of each video, updating the database, until all are ready.

* As each video reaches the ready state, the Huey task copies the thumbnail to Backblaze B2.

* Once a video is indexed, its thumbnail is displayed in the main list of videos.

### Searching Videos

* Users can search on natural language queries such as "cats playing on the floor"

This webinar recording shows a previous version of the website in action and explains how the pieces fit together:

[![Vision Meets Storage: AI-Driven Insights with Twelve Labs](https://cdn.brighttalk.com/ams/california/images/communication/611588/image_974178.png?width=640&height=360)](https://www.brighttalk.com/webcast/14807/611588)

## Prerequisites

* [Python 3.9.2](https://www.python.org/downloads/release/python-392/) (other Python versions _may_ work) and `pip`
* A Backblaze account. [Sign up here](https://www.backblaze.com/b2/sign-up.html?referrer=nopref).
* A TransloadIt account. [Sign up here](https://transloadit.com/c/signup/).
* A Twelve Labs account. [Sign up here](https://playground.twelvelabs.io/).

## Backblaze B2

Click **Buckets** in the navigation menu on the left, then **Create a Bucket**. Give the bucket a name (you may need more than one try, the bucket name must be globally unique!), leave the remaining settings, and click **Create a Bucket**. Make a note of the **Endpoint** shown in the bucket details; it's a domain name of the form `s3.us-west-004.backblazeb2.com`. Make a note also of the region portion of the endpoint; this is the string following `s3.` and preceding `.backblazeb2.com`. In the example above, it's `us-west-004`, but yours may be different. You can use the same bucket for static assets, such as the web app's CSS and JavaScript files, and your videos, or create a bucket for each purpose.  

You'll be creating two Application Keys–one each for TransloadIt and the web application. Why two keys? The two B2 clients need different levels of access: TransloadIt only needs to write raw and processed files; the web app and tasks need read/write access. 

Click **App Keys** in the left nav menu, then **Add a New Application Key**. Name the key `write-only-key-for-transloadit`. Select your bucket, **Write Only** and **Allow List All Bucket Names**, and click **Create New Key**. Again, make careful note of the key!

Add a second Application Key, named `read-write-key-for-video-app`, with **Read and Write** access to the bucket you just created, and **Allow List All Bucket Names**. One more time, copy that key somewhere safe!

## TransloadIt

You can create a new App, or use an existing one, as you see fit.

Click **Credentials** in the navigation menu on the left, then, under **Third-party Credentials** click **Add new Credential**. Select **Backblaze** as the service, name the key `backblaze-write-only`, and paste in the Backblaze B2 Bucket name, Application Key ID and Application Key. Click **Save**.

Now click **Templates** in the left nav menu, then **New Template**. Click **Blank** to create an empty template. Give the template a suitable name and paste in the [assembly instructions](assembly-instructions.json). Click **Create Template** and copy the template id displayed at the top of the page.

Finally, to secure access to your template, click **Settings** in the left nav menu and, under **API Settings**, enable **Require a correct Signature**. The web application contains code to generate a unique signature for each file upload.

## Twelve Labs

Twelve Labs creates a default video index when you sign up. Log in to Twelve Labs and:

* Create an API key in the [Twelve Labs dashboard](https://dashboard.twelvelabs.io/home).

* Click the default index in the [Playground index list](https://playground.twelvelabs.io/indexes) and make a note of the URL. The index ID is the segment of the URL after the last `/`. For example, in the URL `https://playground.twelvelabs.io/indexes/65bad3966dc02a0c60049448`, the index ID is `65bad3966dc02a0c60049448`

## Web Application

### Installation

Clone this repository onto the host, `cd` into the local repository directory, then use `pip install` to install dependencies for the components as required:

```bash
git clone git@github.com:backblaze-b2-samples/b2-twelvelabs-example.git
cd b2-twelvelabs-example
pip install -r requirements.txt
```

### Configuration

Copy `.env.template` to `.env`, or set environment variables with your configuration:

```bash
# Settings for bucket containing videos, thumbnails etc
DEFAULT_ACCESS_KEY_ID="<Backblaze Application Key ID>"
DEFAULT_SECRET_ACCESS_KEY="<Backblaze Application Key>"
DEFAULT_S3_ENDPOINT_URL="<Backblaze bucket endpoint, e.g. s3.us-west-004.backblazeb2.com>"
DEFAULT_S3_REGION_NAME="<Backblaze endpoint region, e.g. us-west-004>"
DEFAULT_STORAGE_BUCKET_NAME="<Backblaze bucket name>"
DEFAULT_STORAGE_LOCATION="<Path to files within bucket>"

# Settings for bucket containing static assets
STATIC_ACCESS_KEY_ID="<Backblaze Application Key ID>"
STATIC_SECRET_ACCESS_KEY="<Backblaze Application Key>"
STATIC_S3_ENDPOINT_URL="<Backblaze bucket endpoint, e.g. s3.us-west-004.backblazeb2.com>"
STATIC_S3_REGION_NAME="<Backblaze endpoint region, e.g. us-west-004>"
STATIC_STORAGE_BUCKET_NAME="<Backblaze bucket name>"
STATIC_STORAGE_LOCATION="<Path to files within bucket>"

TRANSLOADIT_KEY="<Transloadit auth key>"
TRANSLOADIT_SECRET="<Transloadit auth secret>"
TRANSLOADIT_TEMPLATE_ID="<Transloadit template ID>"

TWELVE_LABS_API_KEY="<Twelve Labs API Key>"
TWELVE_LABS_INDEX_ID="<Twelve Labs Index ID>"

WEB_APPLICATION_HOST='<Hostname of the app>'
```

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

### Run the Huey consumer

To start the Huey consumer with a single worker thread:

```bash
python manage.py run_huey
```

Since the tasks spend most of their time waiting on sockets, you will likely want to run multiple greenlet workers, for example:

```bash
python manage.py run_huey --workers=16 --worker-type=greenlet
```

Huey can run workers as threads, processes or [greenlets](https://greenlet.readthedocs.io/en/latest/). See the [Huey consumer documentation](https://huey.readthedocs.io/en/latest/consumer.html) for details. 

## Caveats

Note that this is an example system! To run a similar system in production, you would need to make several changes,
including running the app from a WSGI server such as [Green Unicorn](http://gunicorn.org/)
  or [Apache Web Server](https://httpd.apache.org) with [`mod_wsgi`](https://github.com/GrahamDumpleton/mod_wsgi).

Feel free to fork this repository and submit a pull request if you make an interesting change!

_The web application is based on the [Backblaze B2 Video Sharing Example](https://github.com/backblaze-b2-samples/b2-video-sharing-example), which in turn was originally forked from the 
excellent [simple-s3-setup](https://github.com/sibtc/simple-s3-setup) by [sibtc](https://github.com/sibtc/)_.
