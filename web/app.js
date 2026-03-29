// 1. 连接 ROS
console.log("--00----");
const ros = new ROSLIB.Ros({
    url: "ws://192.168.50.99:9090"
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

/** Web 写入要加载的 launch 文件名，tb3_launch_service 订阅后再响应 /start_tb3_world */
const tb3WorldLaunchTopic = new ROSLIB.Topic({
    ros: ros,
    name: '/tb3_world_launch_file',
    messageType: 'std_msgs/String'
});

const tb3ShowUiTopic = new ROSLIB.Topic({
    ros: ros,
    name: '/tb3_show_ui',
    messageType: 'std_msgs/Bool'
});

const tb3SetParamsSrv = new ROSLIB.Service({
    ros: ros,
    name: '/tb3_launch_service/set_parameters',
    serviceType: 'rcl_interfaces/srv/SetParameters'
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

const startNav2MappingSrv = new ROSLIB.Service({
    ros: ros,
    name: '/start_nav2_slam',
    serviceType: 'std_srvs/srv/Trigger'
});

const stopNav2MappingSrv = new ROSLIB.Service({
    ros: ros,
    name: '/stop_nav2_slam',
    serviceType: 'std_srvs/srv/Trigger'
});

const startNav2AutoMappingSrv = new ROSLIB.Service({
    ros: ros,
    name: '/start_nav2_reflex_explore',
    serviceType: 'std_srvs/srv/Trigger'
});

const stopNav2AutoMappingSrv = new ROSLIB.Service({
    ros: ros,
    name: '/stop_nav2_reflex_explore',
    serviceType: 'std_srvs/srv/Trigger'
});

// 载入地图用 map_server 时，只有 /map_server/map 存在；slam_toolbox 的 dynamic_map 仅在 SLAM 运行时才有
const getMapServiceCandidates = [
    '/map_server/map',
    '/slam_toolbox/dynamic_map',
    '/dynamic_map',
];
let waitingMapAfterLoad = false;
let waitingMapTimer = null;

function setMappingResult(text) {
    const el = document.getElementById('mapping-result');
    if (el) el.innerText = text;
}

function setNav2MappingResult(text) {
    const el = document.getElementById('nav2-mapping-result');
    if (el) el.innerText = text;
}

function setNav2AutoMappingResult(text) {
    const el = document.getElementById('nav2-auto-mapping-result');
    if (el) el.innerText = text;
}

function setMapIoResult(text) {
    const el = document.getElementById('map-io-result');
    if (el) el.innerText = text;
}

function setLoadMapButtonEnabled(enabled) {
    const btn = document.getElementById('btn-load-map');
    if (btn) btn.disabled = !enabled;
}

function setSaveMapButtonEnabled(enabled) {
    const btn = document.getElementById('btn-save-map');
    if (btn) btn.disabled = !enabled;
}

/** 拉取地图完成后，恢复保存/载入按钮 */
function setMapIoButtonsEnabled(enabled) {
    setLoadMapButtonEnabled(enabled);
    setSaveMapButtonEnabled(enabled);
}

function startMapping() {
    stopNav2AutoMapping()
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

function startNav2Mapping() {
    setNav2MappingResult('启动 nav2 建图请求中...');
    const request = new ROSLIB.ServiceRequest({});
    startNav2MappingSrv.callService(request, (result) => {
        console.log('Start nav2 mapping result:', result);
        setNav2MappingResult(
            result?.success
                ? `启动 nav2 建图成功: ${result.message || 'ok'}`
                : `启动 nav2 建图失败: ${result?.message || 'unknown error'}`
        );
    }, (error) => {
        console.error('Start nav2 mapping failed:', error);
        setNav2MappingResult('启动 nav2 建图失败: 服务调用异常');
    });
}

function stopNav2Mapping() {
    setNav2MappingResult('停止 nav2 建图请求中...');
    const request = new ROSLIB.ServiceRequest({});
    stopNav2MappingSrv.callService(request, (result) => {
        console.log('Stop nav2 mapping result:', result);
        setNav2MappingResult(
            result?.success
                ? `停止 nav2 建图成功: ${result.message || 'ok'}`
                : `停止 nav2 建图失败: ${result?.message || 'unknown error'}`
        );
    }, (error) => {
        console.error('Stop nav2 mapping failed:', error);
        setNav2MappingResult('停止 nav2 建图失败: 服务调用异常');
    });
}

function startNav2AutoMapping() {
    stopMapping();
    startNav2Mapping();    

    setNav2AutoMappingResult('启动 nav2 自主建图请求中...');
    const request = new ROSLIB.ServiceRequest({});
    startNav2AutoMappingSrv.callService(request, (result) => {
        console.log('Start nav2 auto mapping result:', result);
        setNav2AutoMappingResult(
            result?.success
                ? `启动 nav2 自主建图成功: ${result.message || 'ok'}`
                : `启动 nav2 自主建图失败: ${result?.message || 'unknown error'}`
        );
    }, (error) => {
        console.error('Start nav2 auto mapping failed:', error);
        setNav2AutoMappingResult('启动 nav2 自主建图失败: 服务调用异常');
    });
}

function stopNav2AutoMapping() {
    stopMapping();
    stopNav2Mapping();   
    setNav2AutoMappingResult('停止 nav2 自主建图请求中...');
    const request = new ROSLIB.ServiceRequest({});
    stopNav2AutoMappingSrv.callService(request, (result) => {
        console.log('Stop nav2 auto mapping result:', result);
        setNav2AutoMappingResult(
            result?.success
                ? `停止 nav2 自主建图成功: ${result.message || 'ok'}`
                : `停止 nav2 自主建图失败: ${result?.message || 'unknown error'}`
        );
        setTimeout(() => {
            teleop(0, 0);
        }, 1500);
    }, (error) => {
        console.error('Stop nav2 auto mapping failed:', error);
        setNav2AutoMappingResult('停止 nav2 自主建图失败: 服务调用异常');
    });
}

function pauseNav2AutoMapping() {
    setNav2AutoMappingResult('暂停 nav2 自主建图请求中...');
    const request = new ROSLIB.ServiceRequest({});
    stopNav2AutoMappingSrv.callService(request, (result) => {
        console.log('Pause nav2 auto mapping result:', result);
        setNav2AutoMappingResult(
            result?.success
                ? `暂停 nav2 自主建图成功: ${result.message || 'ok'}`
                : `暂停 nav2 自主建图失败: ${result?.message || 'unknown error'}`
        );
        setTimeout(() => {
            teleop(0, 0);
        }, 1500);
    }, (error) => {
        console.error('Stop nav2 auto mapping failed:', error);
        setNav2AutoMappingResult('暂停 nav2 自主建图失败: 服务调用异常');
    });
}

/** 保存地图文件名用：YYYYMMDD_HHmmss，便于排序且适合路径 */
function formatMapSaveTimestamp() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

/**
 * 保存地图：ROSLIB 调用 /map_saver/save_map（nav2_msgs/srv/SaveMap），
 * 在 #map-save-base 前缀后追加时间戳作为实际保存名；成功后把对应 .yaml 路径写入 #map-url-load。
 */
function saveMap() {
    const input = document.getElementById('map-save-base');
    const mapBase = (input && String(input.value).trim()) || '';
    if (!mapBase) {
        setMapIoResult('保存地图失败: 请填写保存路径前缀（无扩展名）');
        return;
    }

    const mapBaseWithTs = `${mapBase}_${formatMapSaveTimestamp()}`;

    // setSaveMapButtonEnabled(false);
    setMapIoResult(`保存地图请求中: ${mapBaseWithTs} ...`);

    // const srv = new ROSLIB.Service({
    //     ros: ros,
    //     name: '/slam_toolbox/save_map',
    //     serviceType: 'slam_toolbox/srv/SaveMap'
    // });
    // const req = new ROSLIB.ServiceRequest({ name: { data: mapBaseWithTs } });

    // ros2 service call /map_server/load_map nav2_msgs/srv/LoadMap "{map_url: /ros/maps/map.yaml}"
    // ros2 service call /map_saver/save_map nav2_msgs/srv/SaveMap "{map_topic: map, map_url: my_map, image_format: pgm, map_mode: trinary, free_thresh: 0.25, occupied_thresh: 0.65}"


    const srv = new ROSLIB.Service({
        ros: ros,
        name: '/map_saver/save_map',
        serviceType: 'nav2_msgs/srv/SaveMap'
    });
    const req = new ROSLIB.ServiceRequest({map_topic: "map", map_url: mapBaseWithTs, image_format: "pgm", map_mode: "trinary", free_thresh: 0.15, occupied_thresh: 0.65});

    srv.callService(req, (result) => {
        console.log('saveMap (/map_saver/save_map) result:', result);
        const ok = result?.result === true || result?.result === 1;
        if (ok) {
            const yamlPath = `${mapBaseWithTs}.yaml`;
            const loadInput = document.getElementById('map-url-load');
            if (loadInput) loadInput.value = yamlPath;
            setMapIoResult(
                `保存地图成功: ${mapBaseWithTs}（生成 .yaml / .pgm），已同步载入路径: ${yamlPath}`
            );
        } else {
            setMapIoResult(
                '保存地图失败: SaveMap 返回 false（常见原因：/map 上尚无地图或超时），请先开始建图并等待地图发布'
            );
        }
        setSaveMapButtonEnabled(true);
    }, (error) => {
        console.error('saveMap service call failed:', error);
        setMapIoResult('保存地图失败: 服务调用异常');
        setSaveMapButtonEnabled(true);
    });
}

/**
 * 载入地图：纯 ROSLIB 直连 /map_server/load_map（nav2_msgs/srv/LoadMap），
 * yaml 路径来自 #map-url-load。
 */
function loadMap() {
    const input = document.getElementById('map-url-load');
    const mapUrl = (input && String(input.value).trim()) || '';
    if (!mapUrl) {
        setMapIoResult('载入地图失败: 请填写地图 yaml 路径');
        return;
    }

    // setLoadMapButtonEnabled(false);
    setMapIoResult(`载入地图请求中: ${mapUrl} ...`);

    const srv = new ROSLIB.Service({
        ros: ros,
        name: '/map_server/load_map',
        serviceType: 'nav2_msgs/srv/LoadMap'
    });
    const req = new ROSLIB.ServiceRequest({ map_url: mapUrl });

    srv.callService(req, (result) => {
        console.log('loadMap (/map_server/load_map) result:', result);
        const code = Number(result?.result);
        if (code === 0) {
            setMapIoResult(`载入地图成功: ${mapUrl}，正在拉取地图...........`);
            // fetchMapAfterLoad();

            //直接渲染
            renderMapAndRobot('loadMapCanvas',result.map);
            setMapIoResult(`载入成功，地图已显示`);
            return;
        }
        setMapIoResult(`载入地图失败: result=${Number.isFinite(code) ? code : 'unknown'}`);
        setLoadMapButtonEnabled(true);
    }, (error) => {
        console.error('loadMap service call failed:', error);
        setMapIoResult('载入地图失败: 服务调用异常');
        setLoadMapButtonEnabled(true);
    });
}

function fetchMapAfterLoad() {
    const req = new ROSLIB.ServiceRequest({});
    const serviceTypes = ['nav_msgs/srv/GetMap', 'nav_msgs/GetMap'];
    const serviceNames = [...getMapServiceCandidates];
    const maxRounds = 12;
    const delayMs = 400;

    const callByType = (serviceName, typeIdx, onDone) => {
        if (typeIdx >= serviceTypes.length) {
            onDone(false);
            return;
        }
        const srv = new ROSLIB.Service({
            ros: ros,
            name: serviceName,
            serviceType: serviceTypes[typeIdx]
        });

        srv.callService(req, (resp) => {
            const mapMsg = resp?.map;
            if (!mapMsg || !mapMsg.info || mapMsg.data == null || mapMsg.data.length === undefined) {
                callByType(serviceName, typeIdx + 1, onDone);
                return;
            }
            renderMapAndRobot('loadMapCanvas',mapMsg);
            waitingMapAfterLoad = false;
            if (waitingMapTimer) clearTimeout(waitingMapTimer);
            setMapIoResult(`载入成功，地图已显示（来源: ${serviceName}）`);
            setMapIoButtonsEnabled(true);
            onDone(true);
        }, () => {
            callByType(serviceName, typeIdx + 1, onDone);
        });
    };

    const tryNextService = (idx, onRoundFail) => {
        if (idx >= serviceNames.length) {
            onRoundFail();
            return;
        }
        callByType(serviceNames[idx], 0, (ok) => {
            if (!ok) tryNextService(idx + 1, onRoundFail);
        });
    };

    const runRound = (round) => {
        setMapIoResult(`载入成功，正在拉取地图... (${round}/${maxRounds})`);
        tryNextService(0, () => {
            if (round < maxRounds) {
                setTimeout(() => runRound(round + 1), delayMs);
            } else {
                waitingMapAfterLoad = true;
                setMapIoResult('载入成功，正在等待 /map 话题（lifecycle 激活后可能自动出现）...');
                if (waitingMapTimer) clearTimeout(waitingMapTimer);
                waitingMapTimer = setTimeout(() => {
                    if (waitingMapAfterLoad) {
                        setMapIoResult('载入成功，但未收到地图（请确认 map_server 已 active）');
                        setMapIoButtonsEnabled(true);
                    }
                }, 12000);
            }
        });
    };

    // map_server 为 lifecycle：激活略晚于节点创建，稍后再试 GetMap
    setTimeout(() => runRound(1), 300);
}

/** 下拉选中的 *.world → turtlebot3_gazebo/share/launch 下的 *.launch.py */
function worldWorldToLaunchPy(worldWorld) {
    const w = String(worldWorld || '').trim();
    if (!w.endsWith('.world')) return 'turtlebot3_world.launch.py';
    return `${w.slice(0, -'.world'.length)}.launch.py`;
}

function runSimulation() {
    const sel = document.getElementById('sim-world-launch');
    const worldWorld =
        (sel && String(sel.value).trim()) || 'turtlebot3_world.world';
    const launchFile = worldWorldToLaunchPy(worldWorld);
    const showUiEl = document.getElementById('sim-show-ui');
    const showUi = !!(showUiEl && showUiEl.checked);
    setSimulationResult(
        `运行仿真请求中 (${worldWorld} → ${launchFile}, UI:${showUi ? '开' : '关'})...`
    );

    const request = new ROSLIB.ServiceRequest({});
    const callStart = () => {
        startSimSrv.callService(request, (result) => {
            console.log('Start simulation result:', result);
            setSimulationResult(
                result?.success
                    ? `运行成功: ${result.message || 'ok'}`
                    : `运行失败: ${result?.message || 'unknown error'}`
            );
        }, (error) => {
            console.error('Start simulation failed:', error);
            setSimulationResult('运行失败: 服务调用异常');
        });
    };

    const fallbackThenStart = () => {
        tb3WorldLaunchTopic.publish({ data: launchFile });
        tb3ShowUiTopic.publish({ data: showUi });
        setTimeout(callStart, 80);
    };

    // PARAMETER_STRING=4, PARAMETER_BOOL=1；与 tb3_launch_service 中 tb3_show_ui / world_launch_file 一致
    const paramReq = new ROSLIB.ServiceRequest({
        parameters: [
            {
                name: 'world_launch_file',
                value: { type: 4, string_value: launchFile }
            },
            {
                name: 'tb3_show_ui',
                value: { type: 1, bool_value: showUi }
            }
        ]
    });

    tb3SetParamsSrv.callService(
        paramReq,
        (res) => {
            const results = res && res.results;
            const ok =
                results &&
                results.length > 0 &&
                results.every((r) => r.successful === true);
            if (!ok) {
                console.warn('set_parameters 未全部成功，回退话题同步', res);
                fallbackThenStart();
                return;
            }
            tb3WorldLaunchTopic.publish({ data: launchFile });
            setTimeout(callStart, 80);
        },
        (err) => {
            console.warn('set_parameters 不可用，回退话题同步', err);
            fallbackThenStart();
        }
    );
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

let latestMapMsg = null;
let latestRobotPose = null; // {x, y, yaw, source}
let latestPoseDebugText = '等待位姿数据...';
const autoSubscribedPoseTopics = new Set();

function setPoseDebug(text) {
    latestPoseDebugText = text;
    const el = document.getElementById('pose-debug');
    if (el) el.innerText = text;
}

function subscribeWithTypes(topicName, messageTypes, callback) {
    messageTypes.forEach((messageType) => {
        const sub = new ROSLIB.Topic({
            ros: ros,
            name: topicName,
            messageType: messageType
        });
        sub.subscribe(callback);
    });
}

function handlePoseLikeMessage(msg, source) {
    const p =
        msg?.pose?.pose?.position ||
        msg?.pose?.position ||
        msg?.position;
    const q =
        msg?.pose?.pose?.orientation ||
        msg?.pose?.orientation ||
        msg?.orientation;
    if (!p || !q) return false;
    latestRobotPose = {x: p.x, y: p.y, yaw: yawFromQuaternion(q), source: source};
    setPoseDebug(`source=${source} x=${p.x.toFixed(2)} y=${p.y.toFixed(2)} yaw=${latestRobotPose.yaw.toFixed(2)}`);
    renderMapAndRobot('mapCanvas');
    return true;
}

function autoDiscoverAndSubscribePoseTopics() {
    ros.getTopics((res) => {
        const topics = res?.topics || [];
        const types = res?.types || [];
        const poseRegex = /(amcl_pose|odom|robot_pose|pose|base_pose_ground_truth|localization)/i;
        const matched = [];

        for (let i = 0; i < topics.length; i++) {
            const topic = topics[i];
            const type = types[i] || '';
            if (!poseRegex.test(topic)) continue;
            if (autoSubscribedPoseTopics.has(topic)) continue;
            autoSubscribedPoseTopics.add(topic);
            matched.push(`${topic}(${type})`);

            // 按常见位姿消息结构直接尝试解析，避免过度依赖 type 字符串格式
            const sub = new ROSLIB.Topic({ros: ros, name: topic, messageType: type || 'geometry_msgs/msg/PoseStamped'});
            sub.subscribe((msg) => {
                handlePoseLikeMessage(msg, `auto:${topic}`);
            });
        }

        if (matched.length > 0) {
            setPoseDebug(`自动发现位姿话题: ${matched.join(', ')}`);
        } else if (!latestRobotPose) {
            setPoseDebug('等待位姿数据... 未发现包含 pose/odom/amcl 的话题');
        }
    }, () => {
        if (!latestRobotPose) setPoseDebug('等待位姿数据... 获取 topic 列表失败');
    });
}

// subscribeWithTypes('/amcl_pose', [
//     'geometry_msgs/msg/PoseWithCovarianceStamped',
//     'geometry_msgs/PoseWithCovarianceStamped'
// ], (msg) => {
//     handlePoseLikeMessage(msg, 'amcl');
// });

// subscribeWithTypes('/odom', [
//     'nav_msgs/msg/Odometry',
//     'nav_msgs/Odometry'
// ], (msg) => {
//     // AMCL 可用时优先使用 map 坐标系下的位姿
//     if (latestRobotPose?.source === 'amcl') return;
//     handlePoseLikeMessage(msg, 'odom');
// });

subscribeWithTypes('/tf', [
    'tf2_msgs/msg/TFMessage',
    'tf2_msgs/TFMessage'
], (msg) => {
    if (latestRobotPose?.source === 'amcl') return;
    const transforms = msg.transforms || [];
    for (const t of transforms) {
        const parent = t.header?.frame_id || '';
        const child = t.child_frame_id || '';
        const isBase = child.endsWith('base_link') || child.endsWith('base_footprint');
        const fromMapOrOdom = parent.endsWith('map') || parent.endsWith('odom');
        if (!isBase || !fromMapOrOdom) continue;
        const trans = t.transform?.translation;
        const rot = t.transform?.rotation;
        if (!trans || !rot) continue;
        latestRobotPose = {
            x: trans.x,
            y: trans.y,
            yaw: yawFromQuaternion(rot),
            source: 'tf'
        };
        setPoseDebug(`source=tf x=${trans.x.toFixed(2)} y=${trans.y.toFixed(2)} yaw=${latestRobotPose.yaw.toFixed(2)} parent=${parent} child=${child}`);
        renderMapAndRobot('mapCanvas');
        return;
    }
});

mapSub.subscribe(msg => {
    latestMapMsg = msg;
    // if (waitingMapAfterLoad) {
    //     waitingMapAfterLoad = false;
    //     if (waitingMapTimer) clearTimeout(waitingMapTimer);
    //     setMapIoResult('载入成功，地图已显示（来源: /map 话题）');
    //     setMapIoButtonsEnabled(true);
    // }
    const mapInfo = msg.info;
    const origin = mapInfo.origin?.position;
    const originText = origin ? `origin=(${origin.x.toFixed(2)},${origin.y.toFixed(2)})` : 'origin=unknown';
    setMapIoResult(`载入成功，地图已显示（来源: /map 话题） map=${mapInfo.width}x${mapInfo.height} res=${mapInfo.resolution} ${originText}`);
    renderMapAndRobot('mapCanvas');
});

ros.on('connection', () => {
    // autoDiscoverAndSubscribePoseTopics();
    // setInterval(() => {
    //     if (!latestRobotPose) autoDiscoverAndSubscribePoseTopics();
    // }, 5000);
});

function yawFromQuaternion(q) {
    const siny = 2 * (q.w * q.z + q.x * q.y);
    const cosy = 1 - 2 * (q.y * q.y + q.z * q.z);
    return Math.atan2(siny, cosy);
}

function renderMapAndRobot(canvasId, mapMsg) {
    if (!latestMapMsg && !mapMsg) return;
    if (mapMsg) {
        drawMap(canvasId, mapMsg);
        // drawRobotOnMap(canvasId, mapMsg, latestRobotPose);
    } else {
        drawMap(canvasId, latestMapMsg);
        drawRobotOnMap(canvasId, latestMapMsg, latestRobotPose);
    }

}

/**
 * OccupancyGrid.data 为 int8[]：未知 = -1。
 * rosbridge 常给 Uint8Array，未知字节 0xFF 读成 255；用 Int8Array 同缓冲视图则得到 -1。
 * 普通 JSON 数组可能是 -1 或 255，或 PGM 遗留 205 等。
 */
function getOccupancyCells(data) {
    if (!data) return null;
    if (data instanceof Int8Array) return data;
    if (data instanceof Uint8Array) {
        return new Int8Array(data.buffer, data.byteOffset, data.byteLength);
    }
    return data;
}

function readOccupancyValue(cells, i) {
    if (cells instanceof Int8Array) {
        return cells[i];
    }
    const raw = cells[i];
    let v = typeof raw === 'number' ? raw : parseFloat(String(raw), 10);
    if (Number.isNaN(v)) return -1;
    v = Math.round(v);
    if (v >= 0 && v <= 100) return v;
    if (v === -1) return -1;
    if (v > 127 && v <= 255) return v - 256;
    if (v === 205 || v === 204) return -1;
    if (v < 0) return -1;
    return v;
}

function drawMap(canvasId, msg) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = msg.info.width;
    const height = msg.info.height;
    const cells = getOccupancyCells(msg.data);
    if (!cells || cells.length < width * height) return;

    const scaleX = canvas.width / width;
    const scaleY = canvas.height / height;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const i = x + (height - y - 1) * width; // ROS maps start from bottom-left
            const v = readOccupancyValue(cells, i);
            if (v === -1) {
                ctx.fillStyle = '#b0b0b0';
            } else if (v === 0) {
                ctx.fillStyle = '#fff';
            } else if (v >= 1 && v <= 100) {
                const t = v / 100;
                const c = Math.round(255 * (1 - t));
                ctx.fillStyle = `rgb(${c},${c},${c})`;
            } else {
                ctx.fillStyle = '#b0b0b0';
            }
            ctx.fillRect(x * scaleX, y * scaleY, scaleX, scaleY);
        }
    }
}

function drawRobotOnMap(canvasId, mapMsg, pose) {
    if (!pose) return;
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const info = mapMsg.info;
    const resolution = info.resolution;
    const origin = info.origin?.position;
    if (!origin || !resolution) return;

    const scaleX = canvas.width / info.width;
    const scaleY = canvas.height / info.height;
    const cellX = (pose.x - origin.x) / resolution;
    const cellY = (pose.y - origin.y) / resolution;
    const px = cellX * scaleX;
    const py = canvas.height - cellY * scaleY;
    const inMap = cellX >= 0 && cellX < info.width && cellY >= 0 && cellY < info.height;
    const mapInfoText = `cell=(${cellX.toFixed(1)},${cellY.toFixed(1)}) pixel=(${px.toFixed(1)},${py.toFixed(1)}) inMap=${inMap}`;
    setPoseDebug(`${latestPoseDebugText} | ${mapInfoText}`);

    // 画机器人位置点
    ctx.beginPath();
    ctx.fillStyle = '#ff2d2d';
    ctx.arc(px, py, 5, 0, Math.PI * 2);
    ctx.fill();

    // 画朝向线
    const dirLen = 14;
    const dx = Math.cos(pose.yaw) * dirLen;
    const dy = -Math.sin(pose.yaw) * dirLen;
    ctx.beginPath();
    ctx.strokeStyle = '#ff2d2d';
    ctx.lineWidth = 2;
    ctx.moveTo(px, py);
    ctx.lineTo(px + dx, py + dy);
    ctx.stroke();
}

// 显式导出给 Vue 层调用
window.sendTask = sendTask;
window.runSimulation = runSimulation;
window.stopSimulation = stopSimulation;
window.startMapping = startMapping;
window.stopMapping = stopMapping;
window.startNav2Mapping = startNav2Mapping;
window.stopNav2Mapping = stopNav2Mapping;
window.startNav2AutoMapping = startNav2AutoMapping;
window.stopNav2AutoMapping = stopNav2AutoMapping;
window.pauseNav2AutoMapping = pauseNav2AutoMapping;
window.saveMap = saveMap;
window.loadMap = loadMap;
window.teleop = teleop;
