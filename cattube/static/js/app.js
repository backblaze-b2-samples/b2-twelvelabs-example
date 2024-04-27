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

  const selectionText = document.querySelector("#selection-text");
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

  const savedListener = video.ontimeupdate;
  video.ontimeupdate = () => {
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

function hms(seconds) {
  // ISO string for 3734.56 is "1970-01-01T01:02:14.560Z", so substring(11, 22) gives us HH:mm:ss.ss = "01:02:14.56"
  return new Date(seconds * 1000).toISOString().substring(11, 22);
}

function escapeXml(unsafe) {
  return unsafe.replace(/[<>&'"]/g, function (c) {
    switch (c) {
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '&': return '&amp;';
      case '\'': return '&apos;';
      case '"': return '&quot;';
    }
  });
}

async function loadClips(div, url) {
  const sectionDiv = document.querySelector(`#${div}`);
  const divElement = sectionDiv.querySelector('.expandable');
  fetch(url).then(response => {
    if (!response.ok) {
      response.text().then(text => {
        divElement.innerHTML = `<pre>${escapeXml(text)}</pre>`;
      })
    }
    return response.json();
  }).then(data => {
    console.log(`Fetched ${div} data: ${data}`);
    let content = '';
    for (const value of data) {
      content += `<p onclick="playClip(${value.start}, ${value.end}); return false;">`
          + `${hms(value.start)} - ${hms(value.end)} "${value.value}"</p>`;
    }

    sectionDiv.querySelector('.subhead').innerHTML = (data.length > 0) ? 'Click to play:' : 'None found';
    if (data.length > 5) {
      content += '<p class="read-more"><a href="#" class="button">Read More</a></p>'
    }
    divElement.innerHTML = content;
    if (data.length > 5) {
      divElement.querySelector('.button').onclick = readMore;
    }
  })
}

function fadeOut(el, callback) {
  const fadeEffect = setInterval(function () {
    let opacity = 1;
    if (!el.style.opacity) {
      el.style.opacity = opacity.toString(10);
    } else {
      opacity = parseFloat(el.style.opacity);
    }
    if (opacity > 0) {
      opacity -= 0.04;
      el.style.opacity = opacity.toString(10);
    } else {
      clearInterval(fadeEffect);
      callback(el);
    }
  }, 40);
}

function animate(el, property, target, duration) {
  duration = duration || 400;
  if (duration < 0) {
    throw new RangeError("duration must be greater than or equal to zero.");
  }
  const timeout = 40;
  const initial = parseFloat(window.getComputedStyle(el).getPropertyValue(property));
  const delta = (target - initial) / (duration / timeout);
  const direction = Math.sign(delta);
  const animateEffect = setInterval(function () {
    let current = parseFloat(window.getComputedStyle(el).getPropertyValue(property));
    const distance = (target - current) * direction;
    // If you compare with zero, then you end up looping forever with distance having a small, non-zero number!
    if (distance > 0.5) {
      current = Math.min(current + delta, target);
      el.style.setProperty(property, current.toString(10) + 'px');
    } else {
      clearInterval(animateEffect);
    }
  }, timeout);
}

function getOuterHeight(el) {
  const computedStyle = window.getComputedStyle(el);
  return el.offsetHeight
    + parseInt(computedStyle.getPropertyValue('margin-top'), 10)
    + parseInt(computedStyle.getPropertyValue('margin-bottom'), 10);
}

function readMore(event) {
  // The button link
  const el = event.currentTarget;
  // The paragraph containing the button link
  const p  = el.parentElement;
  // The div containing all the content
  const div = p.parentElement;
  // The other paragraphs
  const ps = div.querySelectorAll("p:not(.read-more)");

  // measure how tall inside should be by adding together heights of all inside paragraphs (except read-more paragraph)
  const totalHeight = Array.from(ps).reduce((sum, el) => sum + getOuterHeight(el), 0);

  // Set height to prevent instant jumpdown when max height is removed
  div.style.height = `${div.offsetHeight.toString()}px`;
  div.style.maxHeight = '9999px';

  // Expand the div
  animate(div, 'height', totalHeight);

  // fade out and remove read-more
  fadeOut(p, (el) => { el.remove(); });

  // prevent jump-down
  return false;
}
