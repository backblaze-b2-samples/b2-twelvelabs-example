let selectedAll = false;

function selectPage(state) {
  document.querySelectorAll("input[type=checkbox]").forEach(element => {
    element.checked = state;
    element.dispatchEvent(new Event('click'))
  });
}

function getToken(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0,name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function updateIndexUI(tasks) {
  let done = true;
  for (const task of tasks) {
    const divVideo = document.querySelector(`div[data-videoid="${task.id}"]`);
    if (divVideo) {
      const divThumbnail = divVideo.querySelector('div.thumbnail');
      const imgThumbnail = divThumbnail.querySelector('img.thumbnail')
      if (task.status === 'Ready') {
        divThumbnail.dataset.status = "";
        imgThumbnail.src = task.thumbnail;
        divVideo.querySelector('input[type=checkbox]')?.remove();
      } else {
        divThumbnail.dataset.status = task.status;
        done = false;
      }
    }
  }
  return done;
}

function getVideoStatus(tasks, callback) {
  console.log("Getting status");
  fetch('api/videos/status', {
    method:'POST',
    headers:{
      'Content-Type': 'application/json',
      'X-CSRFToken': getToken('csrftoken'),
    },
    body:JSON.stringify(tasks)
  }).then((response) => {
    console.log('status:', response.status);
    return response.json();
  }).then((tasks) => {
    console.log('tasks:', tasks);
    let done = callback(tasks);
    if (!done) {
      setTimeout(() => {
        getVideoStatus(tasks, callback);
      }, 1000);
    }
  });
}

function listenForStatusUpdates(tasks) {
  setTimeout(() => {
    getVideoStatus(tasks, updateIndexUI);
  }, 1000);
}

function videosOperation(data, operation, callback) {
  fetch(`api/videos/${operation}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getToken('csrftoken'),
    },
    body: JSON.stringify(data)
  }).then((response) => {
    console.log('status:', response.status);
    return response.json();
  }).then((data) => {
    callback(data)
  });
}

function indexSelectedVideos() {
  selectedVideosOperation('index', data => {
      console.log('tasks:', data);
      listenForStatusUpdates(data);
  });
}

function deleteSelectedVideos() {
  selectedVideosOperation('delete', () => {
      window.location.reload();
  });
}

function selectedVideosOperation(operation, callback) {
  const checked = document.querySelectorAll("input[type=checkbox]:checked");

  let data;
  if (selectedAll) {
    data = { 'selectedAll' : true };
    console.log("selected all");
  } else {
    // Compile list of selected videos
    const selected = [];
    checked.forEach(element => {
      const divThumbnail = element.parentElement;
      const divVideo = divThumbnail.parentElement;

      selected.push(divVideo.dataset.videoid);
      if (operation === 'index') {
        divThumbnail.dataset.status = 'Sending';
      }
    });
    console.log("selected:", selected);

    data = { 'videos': selected };
  }

  // Disable the checkboxes
  checked.forEach(element => element.disabled = true);

  videosOperation(data, operation, callback);
}

function checkboxClicked(videoCount) {
  const checked = document.querySelectorAll("input[type=checkbox]:checked");
  const unchecked = document.querySelectorAll("input[type=checkbox]:not(:checked)");

  document.querySelector("#index").disabled = (checked.length === 0);
  document.querySelector("#delete").disabled = (checked.length === 0);
  document.querySelector("#unselect-page").disabled = (checked.length === 0);

  selectionText = document.querySelector("#selection-text");
  if (unchecked.length === 0) {
    selectionText.innerHTML
        = `${checked.length} videos on this page selected. <a href="#" id="select-all">Select all ${videoCount} videos.</a>`;
    document.querySelector("#select-all").onclick = () => {
      selectedAll = true;
      document.querySelector("#selection-text").innerHTML =
          `All ${videoCount} videos are selected. <a href="#" id="clear-select-all">Clear selection.</a>`;
      document.querySelector("#clear-select-all").onclick = () => {
        document.querySelector("#selection-text").innerHTML = '&nbsp;';
        selectedAll = false;
        selectPage(false);
        return false;
      }
      return false;
    }
  } else {
    selectionText.innerHTML = '&nbsp;';
  }
}

function playClip(start, end) {
  const video = document.querySelector('video');
  video.currentTime = start;
  video.play();

  savedListener = video.ontimeupdate;
  video.ontimeupdate = (event) => {
    if (video.currentTime > end) {
      video.pause();
      video.ontimeupdate = savedListener;
    }
  };
}

async function pollForVideo(id) {
  console.log(`Polling for ${id}`)
  const response = await fetch(`/api/videos/${id}`)
      .then(response => {
        if (response.ok) {
          return response.json();
        }
      });

  if (response?.video) {
    location.reload();
  }
}
