const districts = ["Barcelona", "Ciutat_Vella", "Eixample", "Sants_Montjuic", "Les_Corts", "Sarria_Sant_Gervasi", "Gracia", "Horta_Guinardo", "Nou_Barris", "Sant_Andreu", "Sant_Marti"];

const defaultUser = "PA";
const defaultDistrict = "Barcelona";

let currentUser = defaultUser;
let currentDistrict = defaultDistrict;
let currentDate = null;
let availableDates = {};
let currentView = "standard"; // Track active sub-tab view state

let container;
let img;

let scale = 1;
let baseScale = 1;
let posX = 0;
let posY = 0;

let isDragging = false;
let startX = 0;
let startY = 0;

async function loadDates() {
  try {
    const res = await fetch("dates.json");
    availableDates = await res.json();
  } catch (err) {
    console.error("Error loading dates.json:", err);
    availableDates = {};
  }
}

function fitImageToContainer() {
  if (!img || !container) return;

  const cw = container.clientWidth;
  const ch = container.clientHeight;

  const iw = img.naturalWidth;
  const ih = img.naturalHeight;

  baseScale = Math.min(cw / iw, ch / ih);

  scale = 1;   // IMPORTANT: reset zoom level (not pixel scale)
  posX = 0;
  posY = 0;

  applyTransform();
}

function resetView() {
  scale = 1;
  posX = 0;
  posY = 0;
  applyTransform();
}

function navigate(user) {
  currentDate = null; // reset to latest
  updateURL(user, currentDistrict);
}

function selectDistrict(district) {
  currentDate = null; // reset to latest
  updateURL(currentUser, district);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function selectDate(date) {
  currentDate = date;
  updateURL(currentUser, currentDistrict, date);
}

// Sub-Tab Change Handler
function switchView(viewType) {
  currentView = viewType;
  
  // Update UI sub-navigation button active classes
  document.getElementById("btn-view-standard").classList.toggle("active", viewType === "standard");
  document.getElementById("btn-view-passatges").classList.toggle("active", viewType === "passatges");
  
  render();
}

function updateURL(user, district, date = null) {
  const datePart = date ? `/${date}` : "";
  window.location.hash = `${user}/${district}${datePart}`;
}

function readURL() {
  const hash = window.location.hash.replace("#", "");
  if (!hash) {
    currentUser = defaultUser;
    currentDistrict = defaultDistrict;
    currentDate = null;
    return;
  }
  const parts = hash.split("/");
  currentUser = parts[0] || defaultUser;
  currentDistrict = parts[1] || defaultDistrict;
  currentDate = parts[2] || null;
}

function attachZoomPan() {

  // ZOOM (scroll)
  container.addEventListener("wheel", (e) => {
    e.preventDefault();

    const zoomIntensity = 0.1;
    const delta = e.deltaY < 0 ? 1 : -1;

    scale = Math.min(6, Math.max(0.2, scale + delta * zoomIntensity));

    applyTransform();
  }, { passive: false });

  // DRAG START
  container.addEventListener("mousedown", (e) => {
    isDragging = true;
    startX = e.clientX - posX;
    startY = e.clientY - posY;
  });

  // DRAG MOVE
  window.addEventListener("mousemove", (e) => {
    if (!isDragging) return;

    posX = e.clientX - startX;
    posY = e.clientY - startY;

    applyTransform();
  });

  // DRAG END
  window.addEventListener("mouseup", () => {
    isDragging = false;
  });

}

function applyTransform() {
  if (!img) return;

  img.style.transform = `
    translate(-50%, -50%)
    translate(${posX}px, ${posY}px)
    scale(${baseScale * scale})
  `;
}

/* ---------------- RENDER ---------------- */

function render() {
  readURL();

  const userButtons = document.querySelectorAll(".user-nav button");
  const sliderContainer = document.querySelector(".date-slider-container");

  userButtons.forEach(btn => {
    btn.classList.toggle("active", btn.textContent.trim() === currentUser);
  });

  const mainPicElem = document.getElementById("main_pic");
  const barPicElem = document.getElementById("bar_pic");

  // Determine subfolder based on active view segment selection
  const viewSubPath = currentView === "passatges" ? "passatges/" : "";

  /* reset zoom ONLY when image changes */
  if (mainPicElem) {
    mainPicElem.onload = () => {
      fitImageToContainer();
    };

    if (currentDate) {
      mainPicElem.src =
        `plots/${currentUser}/${viewSubPath}${currentDistrict}-${currentUser}.${currentDate}.png`;
    } else {
      mainPicElem.src =
        `plots/${currentUser}/${viewSubPath}${currentDistrict}-${currentUser}.png`;
    }
  }

  const slider = document.getElementById("dateSlider");
  const label = document.getElementById("dateLabel");
  const ticks = document.getElementById("dateTicks");

  if (slider) {

    const dates =
      (availableDates[currentDistrict] &&
       availableDates[currentDistrict][currentUser]) || [];

    const allDates = [...dates, null];

    slider.min = 0;
    slider.max = allDates.length - 1;

    const currentIndex =
      currentDate
        ? allDates.indexOf(currentDate)
        : allDates.length - 1;

    slider.value = currentIndex;

    label.textContent = currentDate || "Latest";

    slider.oninput = (e) => {
      const idx = parseInt(e.target.value);
      const selectedDate = allDates[idx];
      label.textContent = selectedDate || "Latest";
    };

    slider.onchange = (e) => {
      const idx = parseInt(e.target.value);
      const selectedDate = allDates[idx];
      selectDate(selectedDate);
    };

    ticks.innerHTML = "";

    const numTicks = 5;

    for (let i = 0; i < numTicks; i++) {
      const idx = Math.round(
        i * (allDates.length - 1) / (numTicks - 1)
      );

      const tick = document.createElement("span");
      tick.textContent = allDates[idx] || "Latest";
      ticks.appendChild(tick);
    }
  }


  if (barPicElem) {
    if (currentUser === "Comparison") {
      barPicElem.style.display = "none";
    } else {
      barPicElem.style.display = "block";
    barPicElem.src =
      `stats/${currentUser}/${viewSubPath}stats_bars_${currentDistrict}_${currentUser}.png`;
   }
  }
  /* COMPARISON */
  const compSection = document.getElementById("comparison_section");

  if (currentUser === "Comparison") {
    compSection.style.display = "flex";
    document.getElementById("comp_left_title").textContent = "PA";
    document.getElementById("comp_right_title").textContent = "Hubert";
    
    const barPa = document.getElementById("bar_pa");
    const barHubert = document.getElementById("bar_hubert");

    barPa.style.display = "block";
    barHubert.style.display = "block";
    
    // Added ${viewSubPath} here to point to the correct folder when toggled
    barPa.src = `stats/PA/${viewSubPath}stats_bars_${currentDistrict}_PA.png`;
    barHubert.src = `stats/Hubert/${viewSubPath}stats_bars_${currentDistrict}_Hubert.png`;

    document.getElementById("comp_left").src = `plots/PA/${viewSubPath}${currentDistrict}-PA.png`;
    document.getElementById("comp_right").src = `plots/Hubert/${viewSubPath}${currentDistrict}-Hubert.png`;
  } else {
    compSection.style.display = "none";
  }

  /* SLIDER VISIBILITY */
  if (sliderContainer) {
    sliderContainer.style.display =
      currentUser === "Comparison" ? "none" : "block";
  }

  /* STATS */
  const tableStatsElem = document.getElementById("table_stats");

  if (tableStatsElem) {
    tableStatsElem.style.display = "block";
    const statPrefix = currentView === "passatges" ? "stats-passatges-" : "stats-";

    if (currentDistrict === "Barcelona") {
      tableStatsElem.src = `stats/${currentUser}/${statPrefix}${currentUser}.png`;
    } else {
      tableStatsElem.src =
        `stats/${currentUser}/${statPrefix}${currentDistrict}-${currentUser}.png`;
    }
  }

  /* TIMESERIES */
  const timeseriesElem = document.getElementById("timeseries");

  if (timeseriesElem) {
    if (currentView === "passatges") {
      timeseriesElem.style.display = "none";
    } else {
      timeseriesElem.style.display = "inline-block";
      if (currentUser === "Comparison") {
        timeseriesElem.src = `plots/${currentUser}/timeseries/${currentDistrict}.png`;
      } else {
        timeseriesElem.src = `plots/${currentUser}/timeseries/${currentDistrict}-${currentUser}.png`;
      }
    }
  }

  /* NAV */
  const nav = document.getElementById("districtNav");

  if (nav) {
    nav.innerHTML = "";
    districts.forEach(d => {
      const btn = document.createElement("button");
      btn.textContent = d.replace(/_/g, " ");
      if (d === currentDistrict) btn.classList.add("active");
      btn.onclick = () => selectDistrict(d);
      nav.appendChild(btn);
    });
  }

  /* GRID */
  const grid = document.getElementById("districtGrid");

  if (grid) {
  grid.innerHTML = "";

  districts.forEach(d => {
    const container = document.createElement("div");
    container.className = "district-item";

    const label = document.createElement("div");
    label.textContent = d.replace(/_/g, " ");
    label.className = "district-label";
    label.onclick = () => selectDistrict(d);
    // console.log("district:", d);
    const imgEl = document.createElement("img");
    imgEl.src = `plots/${currentUser}/${viewSubPath}${d}-${currentUser}.png`;
    
    if (d === currentDistrict) {
      imgEl.style.outline = "5px solid #ff4444";
      imgEl.style.outlineOffset = "-5px";
    }

    imgEl.onclick = () => selectDistrict(d);

    container.appendChild(label);
    container.appendChild(imgEl);

    grid.appendChild(container);
  });
  }
}

async function init() {
  await loadDates();

  container = document.getElementById("imageContainer");
  img = document.getElementById("main_pic");

  attachZoomPan();
  render();
}

window.addEventListener("load", init);
window.addEventListener("hashchange", render);
