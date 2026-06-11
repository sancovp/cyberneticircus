// CybernetiCircus Full-Window Graph Visualizer
document.addEventListener("DOMContentLoaded", () => {
    let canvas = null;
    let ctx = null;
    let simulation = null;
    let nodes = [];
    let links = [];
    let hoveredNode = null;
    let mouseX = 0, mouseY = 0;

    let activeIdentity = "";
    let activeStepId = "";
    let activeFocusNodes = new Set();
    let activeFocusLabels = new Set();
    let selectedNode = null;

    function getDistrict(node, W, H) {
        W = W || window.innerWidth;
        H = H || window.innerHeight;
        const panelWidth = selectedNode ? 440 : 0;
        const visibleW = W - panelWidth;
        const r = Math.min(visibleW, H) * 0.22;
        if (node.label === "Cybernet" || node.label === "Identity" || node.label === "Skill") {
            return { name: "GHOST SHELL CUSTOMIZER", x: visibleW * 0.28, y: H * 0.32, r, color: [46, 213, 115] };
        }
        if (node.label === "StateMachine" || node.label === "TraversalStep" || node.label === "ExecutionTrace") {
            return { name: "COMPILER RING", x: visibleW * 0.72, y: H * 0.32, r, color: [160, 100, 255] };
        }
        if (node.label === "SimulationRun") {
            return { name: "THE ARENA", x: visibleW * 0.28, y: H * 0.68, r, color: [255, 80, 140] };
        }
        if (node.label === "Concept") {
            return { name: "SCRIPTURE ARCHIVES", x: visibleW * 0.72, y: H * 0.68, r, color: [255, 140, 0] };
        }
        return null;
    }

    // Initialize visualizer
    initVisualizer();

    // Track mouse movements
    window.addEventListener("resize", resizeCanvas);
    window.addEventListener("mousemove", (e) => {
        if (!canvas) return;
        const r = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        mouseX = (e.clientX - r.left) * ((canvas.width / dpr) / r.width);
        mouseY = (e.clientY - r.top) * ((canvas.height / dpr) / r.height);
        
        hoveredNode = null;
        for (let i = nodes.length - 1; i >= 0; i--) {
            const node = nodes[i];
            if (Math.hypot(node.x - mouseX, node.y - mouseY) < node.r + 8) {
                hoveredNode = node;
                break;
            }
        }
    });


    window.addEventListener("click", (e) => {
        if (!canvas) return;
        // Don't deselect if clicking inside the side panel itself
        if (e.target.closest("#side-panel")) return;
        
        if (hoveredNode) {
            selectNode(hoveredNode);
        } else {
            deselectNode();
        }
    });

    const sidePanel = document.getElementById("side-panel");
    const panelTitle = document.getElementById("panel-title");
    const nodeLabelSpan = document.querySelector(".node-label");
    const propertiesTable = document.getElementById("properties-table");
    const fileViewerSection = document.getElementById("file-viewer-section");
    const fileContentPre = document.getElementById("file-content");

    function selectNode(node) {
        if (selectedNode) {
            selectedNode.fx = null;
            selectedNode.fy = null;
        }
        selectedNode = node;
        
        // Trigger center shift first
        updateSimulationDimensions();
        
        // Pin the node, pushing it left if it would be covered by the panel
        const W = window.innerWidth;
        const panelWidth = 440;
        const visibleW = W - panelWidth;
        if (node.x > visibleW - 50) {
            node.x = visibleW - 100 - Math.random() * 50;
        }
        node.fx = node.x;
        node.fy = node.y;
        
        showSidePanel(node);
    }

    function deselectNode() {
        if (selectedNode) {
            selectedNode.fx = null;
            selectedNode.fy = null;
            selectedNode = null;
        }
        updateSimulationDimensions();
        hideSidePanel();
    }

    function updateSimulationDimensions() {
        if (!simulation) return;
        const W = window.innerWidth;
        const H = window.innerHeight;
        const panelWidth = selectedNode ? 440 : 0;
        const visibleW = W - panelWidth;
        
        simulation.force("x", d3.forceX().x(d => {
            const dist = getDistrict(d, W, H);
            return dist ? dist.x : visibleW / 2;
        }).strength(0.65));
        
        simulation.force("y", d3.forceY().y(d => {
            const dist = getDistrict(d, W, H);
            return dist ? dist.y : H / 2;
        }).strength(0.65));
        
        simulation.alpha(0.3).restart();
    }

    async function showSidePanel(node) {
        if (!sidePanel) return;
        
        nodeLabelSpan.textContent = node.label;
        nodeLabelSpan.style.color = `rgb(${getRGBColorString(node)})`;
        panelTitle.textContent = node.name;
        
        // Build properties table
        propertiesTable.innerHTML = "";
        let filePath = null;
        
        if (node.properties) {
            Object.entries(node.properties).forEach(([key, val]) => {
                if (key === "instruction_file_path" || key === "file_path") {
                    filePath = val;
                }
                
                const tr = document.createElement("tr");
                const tdKey = document.createElement("td");
                tdKey.className = "prop-key";
                tdKey.textContent = key;
                
                const tdVal = document.createElement("td");
                tdVal.className = "prop-val";
                tdVal.textContent = val;
                
                tr.appendChild(tdKey);
                tr.appendChild(tdVal);
                propertiesTable.appendChild(tr);
            });
        }
        
        // Fetch and show file contents if path exists
        if (filePath) {
            fileViewerSection.classList.remove("hidden");
            fileContentPre.textContent = "Loading file content...";
            try {
                const res = await fetch(`/api/file/read?path=${encodeURIComponent(filePath)}`);
                if (res.ok) {
                    const data = await res.json();
                    fileContentPre.textContent = data.content;
                } else {
                    fileContentPre.textContent = `Error loading file: ${res.statusText}`;
                }
            } catch (err) {
                fileContentPre.textContent = `Fetch error: ${err.message}`;
            }
        } else {
            fileViewerSection.classList.add("hidden");
            fileContentPre.textContent = "";
        }
        
        sidePanel.classList.add("open");
    }

    function hideSidePanel() {
        if (sidePanel) {
            sidePanel.classList.remove("open");
        }
    }
    
    // Bind close button
    const closeBtn = document.getElementById("panel-close-btn");
    if (closeBtn) {
        closeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            deselectNode();
        });
    }

    window.selectNodeByName = (name) => {
        const node = nodes.find(n => n.name === name || n.id === name);
        if (node) selectNode(node);
    };
    window.deselectNode = deselectNode;

    function initVisualizer() {
        const container = document.getElementById("graph-visualizer");
        if (!container) return;
        
        container.innerHTML = "";
        canvas = document.createElement("canvas");
        container.appendChild(canvas);
        ctx = canvas.getContext("2d");
        
        resizeCanvas();

        const W = window.innerWidth;
        const H = window.innerHeight;
        const panelWidth = selectedNode ? 440 : 0;
        const visibleW = W - panelWidth;

        simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(85).strength(0.1))
            .force("charge", d3.forceManyBody().strength(-120))
            .force("collision", d3.forceCollide().radius(22))
            .force("x", d3.forceX().x(d => {
                const dist = getDistrict(d, W, H);
                return dist ? dist.x : visibleW / 2;
            }).strength(0.65))
            .force("y", d3.forceY().y(d => {
                const dist = getDistrict(d, W, H);
                return dist ? dist.y : H / 2;
            }).strength(0.65));
            
        // Bind drag behavior
        d3.select(canvas)
            .call(d3.drag()
                .container(canvas)
                .subject(dragsubject)
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
                
        requestAnimationFrame(renderLoop);
    }

    function resizeCanvas() {
        if (!canvas) return;
        const dpr = window.devicePixelRatio || 1;
        canvas.width = window.innerWidth * dpr;
        canvas.height = window.innerHeight * dpr;
        ctx.scale(dpr, dpr);
        
        if (simulation) {
            updateSimulationDimensions();
        }
    }

    function dragsubject(event) {
        for (let i = nodes.length - 1; i >= 0; i--) {
            const node = nodes[i];
            if (Math.hypot(node.x - event.x, node.y - event.y) < node.r + 8) {
                return node;
            }
        }
        return null;
    }

    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }

    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }

    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        // Only release pinning if this is NOT the currently selected node
        if (!selectedNode || event.subject.id !== selectedNode.id) {
            event.subject.fx = null;
            event.subject.fy = null;
        }
    }

    function drawGrid(ctx, W, H) {
        ctx.strokeStyle = "rgba(180, 210, 230, 0.022)";
        ctx.lineWidth = 0.5;
        const gs = 40;
        for (let x = 0; x < W; x += gs) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
        }
        for (let y = 0; y < H; y += gs) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
        }
    }

    function getRGBColor(node) {
        if (node.active_tag === "cybernet") return [46, 213, 115]; // green
        if (node.active_tag === "step") return [0, 210, 255]; // cyan
        if (node.active_tag === "state_machine") return [160, 100, 255]; // purple
        
        if (node.label === "Cybernet") return [46, 213, 115]; 
        if (node.label === "StateMachine") return [160, 100, 255]; 
        if (node.label === "TraversalStep") return [0, 210, 255]; 
        if (node.label === "Identity") return [80, 120, 220]; 
        if (node.label === "Concept") return [255, 140, 0]; // orange
        if (node.label === "Skill") return [255, 215, 0]; // gold
        if (node.label === "ExecutionTrace") return [220, 20, 60]; // pinkish-red
        if (node.label === "SimulationRun") return [255, 80, 140]; // pink
        return [120, 120, 120];
    }

    function getRGBColorString(node) {
        const rgb = getRGBColor(node);
        return `${rgb[0]}, ${rgb[1]}, ${rgb[2]}`;
    }

    function drawBloom(ctx, x, y, r, c, glow, act) {
        const br = r * 6.5 + glow * 15;
        const ba = 0.04 + glow * 0.015 + act * 0.02;
        const g = ctx.createRadialGradient(x, y, 0, x, y, br);
        g.addColorStop(0, `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${ba})`);
        g.addColorStop(0.3, `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${ba * 0.4})`);
        g.addColorStop(1, `rgba(${c[0]}, ${c[1]}, ${c[2]}, 0)`);
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(x, y, br, 0, Math.PI * 2); ctx.fill();
    }

    function drawOrb(ctx, x, y, r, c, act, glow, t, seed, isHov, refMx, refMy, label) {
        const pulse = 0.85 + 0.15 * Math.sin(t * 2.5 + seed);
        const radius = r * pulse;
        
        const lx = (refMx - x), ly = (refMy - y);
        const ld = Math.sqrt(lx * lx + ly * ly) || 1;
        const hxoff = lx / ld * radius * 0.25, hyoff = ly / ld * radius * 0.25;
        
        const bodyG = ctx.createRadialGradient(x + hxoff * 0.5, y + hyoff * 0.5, radius * 0.05, x - hxoff * 0.6, y - hyoff * 0.6, radius);
        bodyG.addColorStop(0, `rgba(${Math.min(255, c[0] + 90 + act * 30)}, ${Math.min(255, c[1] + 90 + act * 30)}, ${Math.min(255, c[2] + 90 + act * 30)}, ${0.95 * pulse})`);
        bodyG.addColorStop(0.3, `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${0.85 * pulse})`);
        bodyG.addColorStop(0.7, `rgba(${~~(c[0] * 0.5)}, ${~~(c[1] * 0.5)}, ${~~(c[2] * 0.5)}, ${0.6 * pulse})`);
        bodyG.addColorStop(1, `rgba(${~~(c[0] * 0.15)}, ${~~(c[1] * 0.15)}, ${~~(c[2] * 0.15)}, 0)`);
        
        ctx.fillStyle = bodyG;
        ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.fill();
        
        const sx = x + hxoff * 0.7, sy = y + hyoff * 0.7;
        const sg = ctx.createRadialGradient(sx, sy, 0, sx, sy, radius * 0.4);
        sg.addColorStop(0, `rgba(255, 255, 255, ${0.55 + act * 0.2})`);
        sg.addColorStop(0.4, `rgba(255, 255, 255, 0.15)`);
        sg.addColorStop(1, `rgba(255, 255, 255, 0)`);
        ctx.beginPath(); ctx.arc(sx, sy, radius * 0.4, 0, Math.PI * 2); ctx.fill();
    }

    function drawDistricts(ctx, W, H, time) {
        const panelWidth = selectedNode ? 440 : 0;
        const visibleW = W - panelWidth;
        const r = Math.min(visibleW, H) * 0.22;

        const districtNames = [
            { name: "GHOST SHELL CUSTOMIZER", key: "customizer", color: [46, 213, 115], x: visibleW * 0.28, y: H * 0.32 },
            { name: "COMPILER RING", key: "compiler", color: [160, 100, 255], x: visibleW * 0.72, y: H * 0.32 },
            { name: "THE ARENA", key: "arena", color: [255, 80, 140], x: visibleW * 0.28, y: H * 0.68 },
            { name: "SCRIPTURE ARCHIVES", key: "archives", color: [255, 140, 0], x: visibleW * 0.72, y: H * 0.68 }
        ];

        districtNames.forEach(dist => {
            // 1. Draw glowing outer dashed circle
            ctx.save();
            ctx.strokeStyle = `rgba(${dist.color[0]}, ${dist.color[1]}, ${dist.color[2]}, 0.045)`;
            ctx.setLineDash([6, 12]);
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.arc(dist.x, dist.y, r, 0, Math.PI * 2);
            ctx.stroke();
            ctx.restore();

            // 2. Draw subtle inner glow
            const g = ctx.createRadialGradient(dist.x, dist.y, r * 0.8, dist.x, dist.y, r);
            g.addColorStop(0, "rgba(0, 0, 0, 0)");
            g.addColorStop(1, `rgba(${dist.color[0]}, ${dist.color[1]}, ${dist.color[2]}, 0.01)`);
            ctx.fillStyle = g;
            ctx.beginPath();
            ctx.arc(dist.x, dist.y, r, 0, Math.PI * 2);
            ctx.fill();

            // 3. Draw center crosshair
            ctx.strokeStyle = `rgba(${dist.color[0]}, ${dist.color[1]}, ${dist.color[2]}, 0.12)`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(dist.x - 8, dist.y); ctx.lineTo(dist.x + 8, dist.y);
            ctx.moveTo(dist.x, dist.y - 8); ctx.lineTo(dist.x, dist.y + 8);
            ctx.stroke();

            // 4. Draw district label with digital scanline feel
            ctx.fillStyle = `rgba(${dist.color[0]}, ${dist.color[1]}, ${dist.color[2]}, 0.35)`;
            ctx.font = "bold 9px 'JetBrains Mono', monospace";
            ctx.textAlign = "center";
            ctx.fillText(dist.name, dist.x, dist.y - r + 15);
        });
    }

    function renderLoop(timestamp) {
        if (!ctx) return;
        
        const W = window.innerWidth;
        const H = window.innerHeight;
        const time = timestamp / 1000;
        
        ctx.clearRect(0, 0, W, H);
        drawGrid(ctx, W, H);
        drawDistricts(ctx, W, H, time);
        
        const largeGraphMode = (nodes.length > 150);
        
        // Draw links
        links.forEach(link => {
            const source = link.source;
            const target = link.target;
            if (source.x && source.y && target.x && target.y) {
                const isActiveTransition = (
                    source.active_tag === "step" || target.active_tag === "step" ||
                    source.highlighted || target.highlighted ||
                    activeFocusNodes.has(source.name) || activeFocusNodes.has(target.name)
                );

                if (largeGraphMode && !isActiveTransition) {
                    ctx.strokeStyle = "rgba(120, 120, 120, 0.05)";
                    ctx.lineWidth = 0.5;
                    ctx.beginPath();
                    ctx.moveTo(source.x, source.y);
                    ctx.lineTo(target.x, target.y);
                    ctx.stroke();
                } else {
                    const grad = ctx.createLinearGradient(source.x, source.y, target.x, target.y);
                    const colorStart = getRGBColorString(source);
                    const colorEnd = getRGBColorString(target);
                    
                    grad.addColorStop(0, `rgba(${colorStart}, 0.22)`);
                    grad.addColorStop(1, `rgba(${colorEnd}, 0.22)`);
                    
                    ctx.strokeStyle = grad;
                    ctx.lineWidth = isActiveTransition ? 1.5 : 0.8;
                    ctx.beginPath();
                    ctx.moveTo(source.x, source.y);
                    ctx.lineTo(target.x, target.y);
                    ctx.stroke();
                    
                    if (isActiveTransition || !largeGraphMode) {
                        const packetCount = 2;
                        for (let j = 0; j < packetCount; j++) {
                            const offset = j / packetCount;
                            const p = (time * 0.22 + (parseInt(source.id) * 0.08 || 0) + offset) % 1.0;
                            const px = source.x + (target.x - source.x) * p;
                            const py = source.y + (target.y - source.y) * p;
                            
                            const G_flow = '01アイウエオ';
                            const charIdx = Math.floor((time * 6 + j) % G_flow.length);
                            const flowChar = G_flow[charIdx];
                            
                            ctx.fillStyle = `rgba(${colorEnd}, 0.75)`;
                            ctx.font = '7px monospace';
                            ctx.fillText(flowChar, px - 2, py + 2);
                        }
                    }
                }
            }
        });
        
        // Draw blooms
        nodes.forEach(node => {
            if (node.x && node.y) {
                const isActive = node.active_tag || node.highlighted || (node === hoveredNode) || activeFocusNodes.has(node.name) || activeFocusNodes.has(node.id);
                if (!largeGraphMode || isActive) {
                    const c = getRGBColor(node);
                    const glow = node.active_tag ? 2.2 : 0.4;
                    const act = node.active_tag === "step" ? 1.6 : 0.1;
                    drawBloom(ctx, node.x, node.y, node.r, c, glow, act);
                }
            }
        });
        
        // Draw node orbs
        nodes.forEach(node => {
            if (node.x && node.y) {
                const c = getRGBColor(node);
                const isActive = node.active_tag || node.highlighted || (node === hoveredNode) || activeFocusNodes.has(node.name) || activeFocusNodes.has(node.id);
                
                if (largeGraphMode && !isActive) {
                    ctx.fillStyle = `rgba(${c[0]}, ${c[1]}, ${c[2]}, 0.55)`;
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, node.r * 0.8, 0, Math.PI * 2);
                    ctx.fill();
                } else {
                    const act = node.active_tag === "step" ? 1.6 : 0.1;
                    const glow = node.active_tag ? 2.2 : 0.4;
                    drawOrb(ctx, node.x, node.y, node.r, c, act, glow, time, node.seed || 0, node === hoveredNode, mouseX, mouseY, node.label);
                }
            }
        });
        
        // Draw labels, focus indicators, overlays
        nodes.forEach(node => {
            if (node.x && node.y) {
                const isHov = (node === hoveredNode);
                const isFocused = activeFocusNodes.has(node.name) || activeFocusNodes.has(node.id) || node.highlighted;
                const isSelected = (selectedNode && selectedNode.id === node.id);

                if (isHov) {
                    ctx.save();
                    ctx.translate(node.x, node.y);
                    ctx.rotate(time * 0.5);
                    const ringR = node.r * 1.9;
                    ctx.strokeStyle = "rgba(255, 180, 80, 0.85)";
                    ctx.lineWidth = 0.9;
                    for (let i = 0; i < 4; i++) {
                        ctx.save();
                        ctx.rotate(Math.PI / 2 * i);
                        ctx.beginPath();
                        ctx.moveTo(ringR * 0.7, -ringR);
                        ctx.lineTo(ringR, -ringR);
                        ctx.lineTo(ringR, -ringR * 0.7);
                        ctx.stroke();
                        ctx.restore();
                    }
                    ctx.restore();
                    
                    ctx.strokeStyle = "rgba(255, 180, 80, 0.4)";
                    ctx.lineWidth = 0.8;
                    ctx.beginPath();
                    ctx.moveTo(node.x + node.r + 4, node.y);
                    const lx = node.x + node.r + 22;
                    const ly = node.y - 18;
                    ctx.lineTo(lx, ly);
                    ctx.lineTo(lx + 130, ly);
                    ctx.stroke();
                    
                    ctx.fillStyle = "rgba(255, 220, 140, 0.98)";
                    ctx.font = "bold 8px 'JetBrains Mono', monospace";
                    ctx.textAlign = "left";
                    ctx.fillText(`${node.label.toUpperCase()}`, lx + 4, ly - 14);
                    
                    ctx.fillStyle = "rgba(180, 210, 230, 0.85)";
                    ctx.font = "8px 'Outfit', sans-serif";
                    ctx.fillText(node.name.length > 22 ? node.name.substring(0, 19) + "..." : node.name, lx + 4, ly - 4);
                } else if (isSelected) {
                    ctx.save();
                    ctx.translate(node.x, node.y);
                    ctx.rotate(time * 0.6);
                    const ringR = node.r * 2.1;
                    ctx.strokeStyle = "rgba(255, 215, 0, 0.95)"; // Gold
                    ctx.lineWidth = 1.2;
                    for (let i = 0; i < 4; i++) {
                        ctx.save();
                        ctx.rotate(Math.PI / 2 * i);
                        ctx.beginPath();
                        ctx.moveTo(ringR * 0.65, -ringR);
                        ctx.lineTo(ringR, -ringR);
                        ctx.lineTo(ringR, -ringR * 0.65);
                        ctx.stroke();
                        ctx.restore();
                    }
                    ctx.restore();
                    
                    ctx.fillStyle = "rgba(255, 215, 0, 0.9)";
                    ctx.font = "bold 7px monospace";
                    ctx.textAlign = "center";
                    ctx.fillText("[ARCHAEOLOGY FOCUS]", node.x, node.y - node.r - 9);
                } else if (isFocused) {
                    ctx.save();
                    ctx.translate(node.x, node.y);
                    ctx.rotate(-time * 0.8 + node.seed * 0.01);
                    const ringR = node.r * 2.2;
                    ctx.strokeStyle = "rgba(180, 90, 255, 0.85)";
                    ctx.lineWidth = 1.0;
                    for (let i = 0; i < 4; i++) {
                        ctx.save();
                        ctx.rotate(Math.PI / 2 * i);
                        ctx.beginPath();
                        ctx.moveTo(ringR * 0.6, -ringR);
                        ctx.lineTo(ringR, -ringR);
                        ctx.lineTo(ringR, -ringR * 0.6);
                        ctx.stroke();
                        ctx.restore();
                    }
                    ctx.restore();
                    
                    ctx.fillStyle = "rgba(210, 150, 255, 0.95)";
                    ctx.beginPath();
                    const dotAngle = time * 2.5 + node.seed;
                    ctx.arc(node.x + Math.cos(dotAngle) * ringR, node.y + Math.sin(dotAngle) * ringR, 2.0, 0, Math.PI * 2);
                    ctx.fill();

                    ctx.fillStyle = "rgba(210, 160, 255, 0.9)";
                    ctx.font = "bold 7px monospace";
                    ctx.textAlign = "center";
                    ctx.fillText("[AGENT FOCUS]", node.x, node.y - node.r - 8);
                } else if (node.active_tag === "step" || node.label === "Cybernet") {
                    ctx.fillStyle = "rgba(180, 210, 230, 0.7)";
                    ctx.font = "8px 'Outfit', sans-serif";
                    ctx.textAlign = "center";
                    ctx.fillText(node.name, node.x, node.y + node.r + 13);
                }
            }
        });
        
        requestAnimationFrame(renderLoop);
    }

    async function drawGraph(name) {
        if (!canvas) initVisualizer();
        if (!canvas) return;
        
        try {
            const url = name ? `/api/graph?name=${name}` : "/api/graph";
            const res = await fetch(url);
            const graph = await res.json();
            
            const rawNodes = graph.nodes;
            const rawLinks = graph.links;

            rawNodes.forEach(node => {
                node.seed = Math.random() * 1000;
                if (node.label === "Cybernet") node.r = 13;
                else if (node.label === "StateMachine") node.r = 10;
                else if (node.label === "TraversalStep") node.r = 8;
                else if (node.label === "Identity") node.r = 7;
                else if (node.label === "SimulationRun") node.r = 6;
                else node.r = 5;
            });

            const largeGraphMode = (rawNodes.length > 150);
            const panelWidth = selectedNode ? 440 : 0;
            const visibleW = window.innerWidth - panelWidth;
            const H = window.innerHeight;

            if (largeGraphMode) {
                simulation.force("charge").strength(-15);
                simulation.force("collision").radius(6);
                simulation.force("link").distance(25);
                simulation.alphaDecay(0.08);
                simulation.force("x", d3.forceX().x(d => {
                    const dist = getDistrict(d);
                    return dist ? dist.x : visibleW / 2;
                }).strength(0.12));
                simulation.force("y", d3.forceY().y(d => {
                    const dist = getDistrict(d);
                    return dist ? dist.y : H / 2;
                }).strength(0.12));
            } else {
                simulation.force("charge").strength(-120);
                simulation.force("collision").radius(22);
                simulation.force("link").distance(70);
                simulation.alphaDecay(0.0228);
                simulation.force("x", d3.forceX().x(d => {
                    const dist = getDistrict(d);
                    return dist ? dist.x : visibleW / 2;
                }).strength(0.18));
                simulation.force("y", d3.forceY().y(d => {
                    const dist = getDistrict(d);
                    return dist ? dist.y : H / 2;
                }).strength(0.18));
            }

            const existingNodes = new Map();
            if (simulation) {
                simulation.nodes().forEach(node => {
                    existingNodes.set(node.id, node);
                });
            }

            nodes = rawNodes.map(node => {
                const existing = existingNodes.get(node.id);
                if (existing) {
                    node.x = existing.x;
                    node.y = existing.y;
                    node.vx = existing.vx;
                    node.vy = existing.vy;
                    node.fx = existing.fx;
                    node.fy = existing.fy;
                    node.seed = existing.seed;
                } else {
                    const dist = getDistrict(node);
                    if (dist) {
                        node.x = dist.x + (Math.random() - 0.5) * 50;
                        node.y = dist.y + (Math.random() - 0.5) * 50;
                    } else {
                        node.x = window.innerWidth / 2 + (Math.random() - 0.5) * 50;
                        node.y = window.innerHeight / 2 + (Math.random() - 0.5) * 50;
                    }
                    node.vx = 0;
                    node.vy = 0;
                }
                return node;
            });

            const nodeById = new Map(nodes.map(n => [n.id, n]));
            links = rawLinks.map(link => {
                return {
                    source: nodeById.get(link.source) || link.source,
                    target: nodeById.get(link.target) || link.target,
                    type: link.type
                };
            }).filter(l => typeof l.source === "object" && typeof l.target === "object");

            simulation.nodes(nodes);
            simulation.force("link").links(links);
            
            // Sync selection reference with updated nodes array
            if (selectedNode) {
                const updatedSelectedNode = nodes.find(n => n.id === selectedNode.id);
                if (updatedSelectedNode) {
                    selectedNode = updatedSelectedNode;
                } else {
                    selectedNode = null;
                    hideSidePanel();
                }
            }

            simulation.alpha(0.3).restart();

        } catch (e) {
            console.error("D3 Draw Error:", e);
        }
    }

    async function syncActiveIdentity() {
        try {
            const res = await fetch("/api/agent_logs");
            const data = await res.json();
            
            // Track active focus targets to highlight on graph
            activeFocusNodes = new Set(data.active_focus_nodes || []);
            activeFocusLabels = new Set(data.active_focus_labels || []);

            // Auto-synchronize graph layout when identity or step changes
            const identityChanged = data.active_cybernet && data.active_cybernet !== activeIdentity;
            const stepChanged = data.active_step_id && data.active_step_id !== activeStepId;
            
            if (identityChanged || stepChanged) {
                activeIdentity = data.active_cybernet || "";
                activeStepId = data.active_step_id || "";
                await drawGraph(activeIdentity);
            } else if (!data.active_cybernet && activeIdentity) {
                activeIdentity = "";
                activeStepId = "";
                await drawGraph(null);
            } else {
                // If nodes are already loaded, dynamically update focus/highlight states in memory for 60fps rendering
                nodes.forEach(node => {
                    node.highlighted = (
                        activeFocusNodes.has(node.name) || 
                        activeFocusNodes.has(node.id) || 
                        activeFocusLabels.has(node.label)
                    );
                });
            }
        } catch (e) {
            console.error("Failed to sync identity state:", e);
        }
    }

    // Refresh layout state every 1500ms
    const syncInterval = setInterval(syncActiveIdentity, 1500);

    window.addEventListener("beforeunload", () => {
        clearInterval(syncInterval);
    });
});
