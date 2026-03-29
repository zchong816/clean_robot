const { createApp } = Vue;

createApp({
  data() {
    return {
      mapUrlLoad: "/tmp/clean_robot_map.yaml",
      mapSaveBase: "/tmp/clean_robot_map",
      simWorldFile: "turtlebot3_world.world",
      /** false=无头 gui:=false headless:=true；true=不传 gui/headless */
      simShowUi: false,
    };
  },
  methods: {
    runSimulation() {
      window.runSimulation();
    },
    stopSimulation() {
      window.stopSimulation();
    },
    startMapping() {
      window.startMapping();
    },
    stopMapping() {
      window.stopMapping();
    },
    startNav2Mapping() {
      window.startNav2Mapping();
    },
    stopNav2Mapping() {
      window.stopNav2Mapping();
    },
    startNav2AutoMapping() {
      window.startNav2AutoMapping();
    },
    pauseNav2AutoMapping() {
      window.pauseNav2AutoMapping();
    },
    stopNav2AutoMapping() {
      window.stopNav2AutoMapping();
    },
    saveMap() {
      window.saveMap();
    },
    loadMap() {
      window.loadMap();
    },
    sendTask(type) {
      window.sendTask(type);
    },
    teleop(linearX, angularZ) {
      window.teleop(linearX, angularZ);
    },
  },
  mounted() {
    // 确保默认值写回到原有输入框，兼容 app.js 直接按 id 读取
    const loadInput = document.getElementById("map-url-load");
    const saveInput = document.getElementById("map-save-base");
    const simWorldSel = document.getElementById("sim-world-launch");
    const simShowUi = document.getElementById("sim-show-ui");
    if (loadInput) loadInput.value = this.mapUrlLoad;
    if (saveInput) saveInput.value = this.mapSaveBase;
    if (simWorldSel) simWorldSel.value = this.simWorldFile;
    if (simShowUi) simShowUi.checked = this.simShowUi;
  },
}).mount("#app");
