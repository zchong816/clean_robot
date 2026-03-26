// 1. 连接 ROS
console.log("--00----");
const ros = new ROSLIB.Ros({
    url: "ws://192.168.77.254:9090"
});

console.log("--11----");
ros.on('connection', () => console.log('Connected to rosbridge.'));
ros.on('error', (error) => console.error('Error connecting to rosbridge:', error));
ros.on('close', () => console.log('Connection to rosbridge closed.'));
console.log("--222----");

// 2. 发布任务
const taskCmd = new ROSLIB.Topic({
    ros: ros,
    name: '/task_command',
    messageType: 'std_msgs/String'
});

function sendTask(type) {
    let msgData = {type: type};
    taskCmd.publish({data: JSON.stringify(msgData)});
    console.log("Sent task:", msgData);
}

// 2.1 调用仿真启动服务
const startSimSrv = new ROSLIB.Service({
    ros: ros,
    name: '/start_tb3_world',
    serviceType: 'std_srvs/srv/Trigger'
});

const stopSimSrv = new ROSLIB.Service({
    ros: ros,
    name: '/stop_tb3_world',
    serviceType: 'std_srvs/srv/Trigger'
});

function setSimulationResult(text) {
    const el = document.getElementById('sim-result');
    if (el) el.innerText = text;
}

const startMappingSrv = new ROSLIB.Service({
    ros: ros,
    name: '/start_slam_online_async',
    serviceType: 'std_srvs/srv/Trigger'
});

const stopMappingSrv = new ROSLIB.Service({
    ros: ros,
    name: '/stop_slam_online_async',
    serviceType: 'std_srvs/srv/Trigger'
});

function setMappingResult(text) {
    const el = document.getElementById('mapping-result');
    if (el) el.innerText = text;
}

function startMapping() {
    setMappingResult('开始建图请求中...');
    const request = new ROSLIB.ServiceRequest({});
    startMappingSrv.callService(request, (result) => {
        console.log('Start mapping result:', result);
        setMappingResult(result?.success ? `开始建图成功: ${result.message || 'ok'}` : `开始建图失败: ${result?.message || 'unknown error'}`);
    }, (error) => {
        console.error('Start mapping failed:', error);
        setMappingResult('开始建图失败: 服务调用异常');
    });
}

function stopMapping() {
    setMappingResult('停止建图请求中...');
    const request = new ROSLIB.ServiceRequest({});
    stopMappingSrv.callService(request, (result) => {
        console.log('Stop mapping result:', result);
        setMappingResult(result?.success ? `停止建图成功: ${result.message || 'ok'}` : `停止建图失败: ${result?.message || 'unknown error'}`);
    }, (error) => {
        console.error('Stop mapping failed:', error);
        setMappingResult('停止建图失败: 服务调用异常');
    });
}

function runSimulation() {
    setSimulationResult('运行仿真请求中...');
    const request = new ROSLIB.ServiceRequest({});
    startSimSrv.callService(request, (result) => {
        console.log('Start simulation result:', result);
        setSimulationResult(result?.success ? `运行成功: ${result.message || 'ok'}` : `运行失败: ${result?.message || 'unknown error'}`);
    }, (error) => {
        console.error('Start simulation failed:', error);
        setSimulationResult('运行失败: 服务调用异常');
    });
}

function stopSimulation() {
    setSimulationResult('停止仿真请求中...');
    const request = new ROSLIB.ServiceRequest({});
    stopSimSrv.callService(request, (result) => {
        console.log('Stop simulation result:', result);
        setSimulationResult(result?.success ? `停止成功: ${result.message || 'ok'}` : `停止失败: ${result?.message || 'unknown error'}`);
    }, (error) => {
        console.error('Stop simulation failed:', error);
        setSimulationResult('停止失败: 服务调用异常');
    });
}

// 3. 发布遥控命令
const cmdVel = new ROSLIB.Topic({
    ros: ros,
    name:'/cmd_vel',
    messageType:'geometry_msgs/Twist'
});

function teleop(linearX, angularZ) {
    cmdVel.publish({linear:{x:linearX, y:0, z:0}, angular:{x:0, y:0, z:angularZ}});
}

// 4. 订阅机器人状态
const stateSub = new ROSLIB.Topic({
    ros: ros,
    name:'/robot_state',
    messageType:'std_msgs/String'
});

stateSub.subscribe(msg => {
    document.getElementById('robot-state').innerText = msg.data;
});

// 5. 订阅电池状态
const batterySub = new ROSLIB.Topic({
    ros: ros,
    name:'/battery_state',
    messageType:'std_msgs/String'
});

batterySub.subscribe(msg => {
    const raw = String(msg.data).trim();
    const num = Number(raw);
    document.getElementById('battery').innerText = Number.isFinite(num) ? `${num}%` : raw;
});

// 6. 订阅地图数据
const mapSub = new ROSLIB.Topic({
    ros: ros,
    name:'/map',
    messageType:'nav_msgs/OccupancyGrid'
});

mapSub.subscribe(msg => drawMap(msg));

function drawMap(msg) {
    const canvas = document.getElementById('mapCanvas');
    const ctx = canvas.getContext('2d');
    const width = msg.info.width;
    const height = msg.info.height;
    const data = msg.data;

    const scaleX = canvas.width / width;
    const scaleY = canvas.height / height;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const i = x + (height - y - 1) * width; // ROS maps start from bottom-left
            const val = data[i];
            if (val === -1) ctx.fillStyle = '#ccc';       // unknown
            else if (val === 0) ctx.fillStyle = '#fff';  // free
            else ctx.fillStyle = '#000';                 // occupied
            ctx.fillRect(x * scaleX, y * scaleY, scaleX, scaleY);
        }
    }
}
