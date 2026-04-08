const districts = ["Limoges", "Centre/Hôtel de Ville/Emailleurs", "Aurence/Corgnac/Cité U/Beaublanc", "Louyat/Vigenal", "La Bastide/La Brégère", "Bénédictins/Montplaisir", "Le Sablard/Limoges Sud", "Puy Las Rodas/Renoir", "Vanteaux/CHU", "Landouge", "Beaubreuil/Limoges Nord", "Beaune les Mines"];

const defaultUser = "Béatrice";
const defaultDistrict = "Limoges";

let currentUser = defaultUser;
let currentDistrict = defaultDistrict;

function navigate(user) {
  updateURL(user, currentDistrict);
}

function selectDistrict(district) {
  updateURL(currentUser, district);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateURL(user, district) {
  window.location.hash = `${user}/${district}`;
}

function readURL() {
  const hash = window.location.hash.replace("#", "");
  if (!hash) {
    currentUser = defaultUser;
    currentDistrict = defaultDistrict;
    return;
  }
  const parts = hash.split("/");
  currentUser = parts[0] || defaultUser;
  currentDistrict = parts[1] || defaultDistrict;
}

function render() {
  readURL();

  // 1. Highlight User Buttons
  const userButtons = document.querySelectorAll(".user-nav button");
  userButtons.forEach(btn => {
    btn.classList.toggle("active", btn.textContent.trim() === currentUser);
  });

  // 2. Main Picture
  const mainPicElem = document.getElementById("main_pic");
  const barPicElem = document.getElementById("bar_pic");
  if (currentUser !== "Comparison") {
    if (barPicElem) {
      barPicElem.style.display = "block";
      barPicElem.src = `stats/${currentUser}/stats_bars_${currentDistrict}_${currentUser}.png`;
    }
    if (mainPicElem) {
      mainPicElem.src = `plots/${currentUser}/${currentDistrict}-${currentUser}.png`;
    }
  } else {
    // Hide the top-section side bar when in Comparison mode
    if (barPicElem) barPicElem.style.display = "none";
    if (mainPicElem) mainPicElem.src = `plots/${currentUser}/${currentDistrict}-${currentUser}.png`;
  }

  // 3. Comparison Section Logic
  const compSection = document.getElementById("comparison_section");
  const compLeft = document.getElementById("comp_left");
  const compRight = document.getElementById("comp_right");


  compSection.style.display = "none";
  

  // 4. Stats and Timeseries
  const tableStatsElem = document.getElementById("table_stats");
 if (currentUser != "Comparison") {
  if (tableStatsElem) {
    if (currentDistrict == "Limoges") {
      tableStatsElem.src = `stats/${currentUser}/stats-${currentUser}.png`;
    } else {
      tableStatsElem.src = `stats/${currentUser}/stats-${currentDistrict}-${currentUser}.png`;
    }
  }
 } else {
   tableStatsElem.style.display = "none";
 }

  const timeseriesElem = document.getElementById("timeseries");
  if (timeseriesElem) {
    if (currentUser === "Comparison") {
      timeseriesElem.src = `plots/${currentUser}/timeseries/${currentDistrict}.png`;
    } else {
      timeseriesElem.src = `plots/${currentUser}/timeseries/${currentDistrict}-${currentUser}.png`;
    }
  }

  // 5. Header District Buttons
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

  // 6. Bottom Grid
  const grid = document.getElementById("districtGrid");
  if (grid) {
    grid.innerHTML = "";
    districts.forEach(d => {
      const img = document.createElement("img");
      img.src = `plots/${currentUser}/${d}-${currentUser}.png`;
      if (d === currentDistrict) {
        img.style.outline = "5px solid #ff4444";
        img.style.outlineOffset = "-5px";
      }
      img.onclick = () => selectDistrict(d);
      grid.appendChild(img);
    });
  }
}

function init() { render(); }
window.addEventListener("load", init);
window.addEventListener("hashchange", render);