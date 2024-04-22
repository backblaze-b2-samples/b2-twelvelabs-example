function selectAll() {
  document.querySelectorAll("input[type=checkbox]").forEach(element => {
    element.checked = true;
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
    const divVideo = document.querySelector(`div[data-video="${task.video}"]`);
    const divThumbnail = divVideo.querySelector('div.thumbnail');
    if (task.status === 'Ready') {
      divThumbnail.dataset.status = "";
      divVideo.querySelector('input[type=checkbox]')?.remove();
    } else {
      divThumbnail.dataset.status = task.status;
      done = false;
    }
  }
  return done;
}

function getVideoStatus(tasks, callback) {
  console.log("Getting status");
  fetch('api/videos/get_status', {
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

function indexVideos(selected) {
  fetch('api/videos/index_videos', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getToken('csrftoken'),
    },
    body: JSON.stringify(selected)
  }).then((response) => {
    console.log('status:', response.status);
    return response.json();
  }).then((tasks) => {
    console.log('tasks:', tasks);
    listenForStatusUpdates(tasks);
  });
}

function indexSelectedVideos() {
  // Compile list of selected videos
  const checked = document.querySelectorAll("input[type=checkbox]:checked");
  const selected = [];
  checked.forEach(element => {
    const div = element.parentElement;
    selected.push(div.dataset.video);
    div.querySelector('div.thumbnail').dataset.status = 'Sending';
  });
  console.log("selected:", selected);

  // Disable the checkboxes
  checked.forEach(element => element.disabled = true);

  indexVideos(selected);
}

function checkboxClicked() {
  const checked = document.querySelectorAll("input[type=checkbox]:checked");
  document.querySelector("#index").disabled = (checked.length === 0);
}

window.onload = () => {
  document.querySelector("#select-all").disabled = (document.querySelectorAll("input[type=checkbox]").length === 0);

  const indexing = document.querySelectorAll('div.thumbnail:not([data-status=""]):not([data-status="Ready"])');
  if (indexing.length > 0) {
    const tasks = Array.from(indexing, thumbnail => { return { video: thumbnail.parentElement.dataset.video} })
    listenForStatusUpdates(tasks);
  }
};
