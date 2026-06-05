const districts = ["Barcelona", "Ciutat_Vella", "Eixample", "Sants_Montjuic", "Les_Corts", "Sarria_Sant_Gervasi", "Gracia", "Horta_Guinardo", "Nou_Barris", "Sant_Andreu", "Sant_Marti"];

const defaultUser = "PA";
const defaultDistrict = "Barcelona";

let currentUser = defaultUser;
let currentDistrict = defaultDistrict;
let currentDate = null;
let availableDates = {};
let currentView = "standard"; // 🔄 Tracking active sub-tab state view

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

  scale = 1;   // reset zoom level
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

function applyTransform() {
  if (!img) return;
  img.style.transform = `translate(${posX}px, ${posY}px) scale(${baseScale * scale})`;
}

function selectDistrict(district) {
  updateURL(currentUser, district);
}

function selectDate(date) {
  currentDate = date;
  render();
}

// 🔄 NEW: View Tab Change Action Click Handler
function switchView(viewType) {
  currentView = viewType;
  
  // Update view sub-tab button active layout indicators
  document.getElementById("btn-view-standard").classList.toggle("active", viewType === "standard");
  document.getElementById("btn-view-passatges").classList.toggle("active", viewType === "passatges");
  
  render();
}

function navigate(user) {
  currentDate = null; // reset to latest snapshot on user swap
  updateURL(user, currentDistrict);
}

function updateURL(user, district) {
  const url = new URL(window.location);
  url.searchParams.set("user", user);
  url.searchParams.set("district", district);
  window.history.pushState({}, "", url);
  render();
}

function readURL() {
  const params = new URLSearchParams(window.location.search);
  currentUser = params.get("user") || defaultUser;
  currentDistrict = params.get("district") || defaultDistrict;
}

function render() {
  readURL();

  const userButtons = document.querySelectorAll(".user-nav button");
  const sliderContainer = document.querySelector(".date-slider-container");

  userButtons.forEach(btn => {
    btn.classList.toggle("active", btn.textContent.trim() === currentUser);
  });

  const mainPicElem = document.getElementById("main_pic");
  const barPicElem = document.getElementById("bar_pic");

  // Determine subfolder based on current active view segment selection
  const viewSubPath = currentView === "passatges" ? "passatges/" : "";

  /* MAIN IMAGE MAPS */
  if (mainPicElem) {
    if (currentDate) {
      mainPicElem.src = `plots/${currentUser}/${viewSubPath}${currentDistrict}-${currentUser}.${currentDate}.png`;
    } else {
      mainPicElem.src = `plots/${currentUser}/${viewSubPath}${currentDistrict}-${currentUser}.png`;
    }
  }

  /* DATE SLIDER SELECTION */
  const slider = document.getElementById("dateSlider");
  const label = document.getElementById("dateLabel");
  const ticks = document.getElementById("dateTicks");

  if (slider) {
    const dates = (availableDates[currentDistrict] && availableDates[currentDistrict][currentUser]) || [];
    const allDates = [...dates, null];
    slider.min = 0;
    slider.max = allDates.length - 1;
    const currentIndex = currentDate ? allDates.indexOf(currentDate) : allDates.length - 1;
    slider.value = currentIndex >= 0 ? currentIndex : allDates.length - 1;
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
    const numTicks = Math.min(5, allDates.length);
    for (let i = 0; i < numTicks; i++) {
      const idx = Math.round(i * (allDates.length - 1) / (numTicks - 1));
      const tick = document.createElement("span");
      tick.textContent = allDates[idx] || "Latest";
      ticks.appendChild(tick);
    }
  }

  /* SIDE VERTICAL BAR METER CHART */
  if (barPicElem) {
    // Hide side bar meters during passatges views
    if (currentUser === "Comparison" || currentView === "passatges") {
      barPicElem.style.display = "none";
    } else {
      barPicElem.style.display = "block";
      barPicElem.src = `stats/${currentUser}/stats_bars_${currentDistrict}_${currentUser}.png`;
    }
  }

  /* COMPARISON VIEW PANEL BLOCKS */
  const compSection = document.getElementById("comparison_section");
  if (currentUser === "Comparison") {
    compSection.style.display = "flex";

    const barPa = document.getElementById("bar_pa");
    const barHubert = document.getElementById("bar_hubert");

    if (currentView === "passatges") {
      barPa.style.display = "none";
      barHubert.style.display = "none";
    } else {
      barPa.style.display = "block";
      barHubert.style.display = "block";
      barPa.src = `stats/PA/stats_bars_${currentDistrict}_PA.png`;
      barHubert.src = `stats/Hubert/stats_bars_${currentDistrict}_Hubert.png`;
    }

    document.getElementById("comp_left").src = `plots/PA/${viewSubPath}${currentDistrict}-PA.png`;
    document.getElementById("comp_right").src = `plots/Hubert/${viewSubPath}${currentDistrict}-Hubert.png`;
  } else {
    compSection.style.display = "none";
  }

  /* DATE SLIDER CONTAINER CONTAINER VISIBILITY */
  if (sliderContainer) {
    sliderContainer.style.display = currentUser === "Comparison" ? "none" : "block";
  }

  /* DYNAMIC RENDER OF THE GENERATED STATS IMAGES */
  const tableStatsElem = document.getElementById("table_stats");
  if (tableStatsElem) {
    tableStatsElem.style.display = "block";
    const statPrefix = currentView === "passatges" ? "stats-passatges-" : "stats-";

    if (currentDistrict === "Barcelona") {
      tableStatsElem.src = `stats/${currentUser}/${statPrefix}${currentUser}.png`;
    } else {
      tableStatsElem.src = `stats/${currentUser}/${statPrefix}${currentDistrict}-${currentUser}.png`;
    }
  }

  /* HISTORICAL TIME-SERIES GRAPHS */
  const timeseriesElem = document.getElementById("timeseries");
  if (timeseriesElem) {
    // Hide timeseries in passatges view since the backend does not output passatges lines
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

  /* SUB DISTRICT SELECTION BUTTON BAR BAR */
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

  /* LOWER MAPPED ARCHIVE FOOTER PHOTO GRID OVERVIEW */
  const grid = document.getElementById("districtGrid");
  if (grid) {
    grid.innerHTML = "";
    districts.forEach(d => {
      const imgEl = document.createElement("img");
      imgEl.src = `plots/${currentUser}/${viewSubPath}${d}-${currentUser}.png`;

      if (d === currentDistrict) {
        imgEl.style.outline = "5px solid #ff4444";
        imgEl.style.outlineOffset = "-5px";
      }
      imgEl.onclick = () => selectDistrict(d);
      grid.appendChild(imgEl);
    });
  }
}

async function init() {
  await loadDates();

  container = document.getElementById("imageContainer");
  img = document.getElementById("main_pic");

  if (container && img) {
    window.addEventListener("resize", fitImageToContainer);

    container.addEventListener("mousedown", (e) => {
      if (e.target === img || e.target === container) {
        isDragging = true;
        startX = e.clientX - posX;
        startY = e.clientY - posY;
        container.style.cursor = "grabbing";
        e.preventDefault();
      }
    });

    window.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      posX = e.clientX - startX;
      posY = e.clientY - startY;
      applyTransform();
    });

    window.addEventListener("mouseup", () => {
      isDragging = false;
      if (container) container.style.cursor = "grab";
    });

    container.addEventListener("wheel", (e) => {
      e.preventDefault();
      const zoomFactor = 1.1;
      if (e.deltaY < 0) {
        scale *= zoomFactor;
      } else {
        scale /= zoomFactor;
      }
      scale = Math.max(0.5, Math.min(scale, 20));
      applyTransform();
    }, { passive: false });
  }

  render();
}

window.addEventListener("popstate", render);
window.addEventListener("DOMContentLoaded", init);