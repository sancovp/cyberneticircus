// CybernetiCircus Full-Window Graph Visualizer
document.addEventListener("DOMContentLoaded", () => {
    let canvas = null;
    let ctx = null;
    let simulation = null;
    let zoom = null;
    let currentTransform = d3.zoomIdentity;
    let nodes = [];
    let links = [];
    
    Object.defineProperty(window, 'debugNodes', {
        get: () => nodes,
        configurable: true
    });
    Object.defineProperty(window, 'debugLinks', {
        get: () => links,
        configurable: true
    });
    Object.defineProperty(window, 'activeFocusNodes', {
        get: () => activeFocusNodes,
        configurable: true
    });

    let hoveredNode = null;
    let mouseX = 0, mouseY = 0;

    let activeIdentity = "";
    let activeStepId = "";
    let activeFocusNodes = new Map();
    let activeFocusLabels = new Map();
    let selectedNode = null;
    let originalNodes = null;
    let originalLinks = null;

    function hslToRgb(h, s, l) {
        h /= 360; s /= 100; l /= 100;
        let r, g, b;
        if (s === 0) {
            r = g = b = l; // achromatic
        } else {
            const hue2rgb = (p, q, t) => {
                if (t < 0) t += 1;
                if (t > 1) t -= 1;
                if (t < 1/6) return p + (q - p) * 6 * t;
                if (t < 1/2) return q;
                if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
                return p;
            };
            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;
            r = hue2rgb(p, q, h + 1/3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1/3);
        }
        return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
    }

    let domainDistricts = new Map();

    function recalculateDynamicDistricts() {
        const W = window.innerWidth;
        const H = window.innerHeight;
        
        // Gather all unique domains and subdomains from current nodes
        const domainsMap = new Map();
        
        nodes.forEach(node => {
            let dom = node.properties && node.properties.domain;
            let sub = node.properties && node.properties.subdomain;
            
            // Default if missing
            if (!dom) {
                if (node.label === "Cybernet" || node.label === "Identity" || node.label === "Skill" ||
                    node.label === "StateMachine" || node.label === "TraversalStep" || node.label === "ExecutionTrace" ||
                    node.label === "SimulationRun" || node.label === "TraversalState" || node.label === "ExecutionState") {
                    dom = "cyberneticity";
                } else {
                    dom = "general";
                }
            }
            if (!sub) {
                if (node.label) sub = node.label.toLowerCase();
                else sub = "core";
            }
            
            node.resolvedDomain = dom;
            node.resolvedSubdomain = sub;
            
            if (!domainsMap.has(dom)) {
                domainsMap.set(dom, new Set());
            }
            domainsMap.get(dom).add(sub);
        });
        
        // Ensure cyberneticity exists
        if (!domainsMap.has("cyberneticity")) {
            domainsMap.set("cyberneticity", new Set(["core"]));
        }
        
        const uniqueDomains = Array.from(domainsMap.keys());
        const N = uniqueDomains.length;
        
        const R = Math.min(W, H) * 0.28;
        const centerX = W / 2;
        const centerY = H / 2;
        
        domainDistricts.clear();
        
        uniqueDomains.forEach((domName, i) => {
            let cx = centerX;
            let cy = centerY;
            if (N > 1) {
                const angle = (i * 2 * Math.PI) / N;
                cx = centerX + R * Math.cos(angle);
                cy = centerY + R * Math.sin(angle);
            }
            
            const hue = (i * 360 / N) % 360;
            const color = hslToRgb(hue, 85, 55);
            
            const subSet = domainsMap.get(domName);
            const subList = Array.from(subSet);
            const M = subList.length;
            const subMap = new Map();
            const rSub = 70; // offset radius for subdomains
            
            subList.forEach((subName, j) => {
                let sx = cx;
                let sy = cy;
                if (M > 1) {
                    const subAngle = (j * 2 * Math.PI) / M;
                    sx = cx + rSub * Math.cos(subAngle);
                    sy = cy + rSub * Math.sin(subAngle);
                } else if (M === 1) {
                    sx = cx + 25;
                    sy = cy + 25;
                }
                subMap.set(subName, { x: sx, y: sy });
            });
            
            domainDistricts.set(domName, {
                name: domName.toUpperCase().replace(/_/g, " "),
                x: cx,
                y: cy,
                color: color,
                subdomains: subMap
            });
        });
    }

    function getDistrict(node) {
        const dom = node.resolvedDomain || "cyberneticity";
        const sub = node.resolvedSubdomain || "core";
        const dist = domainDistricts.get(dom);
        if (!dist) return null;
        
        const subCoords = dist.subdomains.get(sub);
        return {
            name: dist.name,
            x: subCoords ? subCoords.x : dist.x,
            y: subCoords ? subCoords.y : dist.y,
            color: dist.color
        };
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
        
        const adjustedMouseX = (mouseX - currentTransform.x) / currentTransform.k;
        const adjustedMouseY = (mouseY - currentTransform.y) / currentTransform.k;
        hoveredNode = null;
        for (let i = nodes.length - 1; i >= 0; i--) {
            const node = nodes[i];
            if (Math.hypot(node.x - adjustedMouseX, node.y - adjustedMouseY) < node.r + 8) {
                hoveredNode = node;
                break;
            }
        }
    });


    // Global click listener removed; click logic is bound directly to the canvas in initVisualizer to prevent panning drag interruptions.

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
        node.fx = node.x;
        node.fy = node.y;
        
        showSidePanel(node);
        
        showNodeSubgraph(node);

        if (zoom && canvas) {
            const W = window.innerWidth;
            const H = window.innerHeight;
            const k = currentTransform.k;
            const tx = (W - 440) / 2 - node.x * k;
            const ty = H / 2 - node.y * k;
            
            d3.select(canvas).transition()
                .duration(750)
                .ease(d3.easeCubicInOut)
                .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(k));
        }
    }

    function deselectNode() {
        if (selectedNode) {
            selectedNode.fx = null;
            selectedNode.fy = null;
            selectedNode = null;
        }
        hideSidePanel();
        
        restoreFullGraph();

        if (zoom && canvas) {
            d3.select(canvas).transition()
                .duration(750)
                .ease(d3.easeCubicInOut)
                .call(zoom.transform, d3.zoomIdentity);
        }
    }

    async function showNodeSubgraph(node) {
        try {
            if (!originalNodes || !originalLinks) {
                originalNodes = [...nodes];
                originalLinks = [...links];
            }
            
            const res = await fetch(`/api/node/subgraph?node_id=${node.id}`);
            const data = await res.json();
            
            const subNodes = data.nodes;
            const subLinks = data.links;
            
            const surfacedReachableIds = new Set();
            const queue = [node.id];
            surfacedReachableIds.add(node.id);
            while (queue.length > 0) {
                const currId = queue.shift();
                for (const link of originalLinks) {
                    const srcId = (typeof link.source === "object") ? link.source.id : link.source;
                    const tgtId = (typeof link.target === "object") ? link.target.id : link.target;
                    if (srcId === currId) {
                        if (!surfacedReachableIds.has(tgtId)) {
                            surfacedReachableIds.add(tgtId);
                            queue.push(tgtId);
                        }
                    }
                }
            }
            
            const nodeById = new Map(originalNodes.map(n => [n.id, n]));
            const subNodeById = new Map();
            const updatedNodes = [];
            
            subNodes.forEach(n => {
                const isClickedNode = n.id === node.id;
                const isReachable = surfacedReachableIds.has(n.id);
                const wasSurfacedInLast20 = (n.name && activeFocusNodes.has(n.name)) || (n.id && activeFocusNodes.has(n.id));
                
                // Show only: clicked node OR currently surfaced reachable node OR database subgraph node not surfaced in the last 20 queries
                if (isClickedNode || isReachable || !wasSurfacedInLast20) {
                    const existing = nodeById.get(n.id);
                    if (existing) {
                        n.x = existing.x;
                        n.y = existing.y;
                        n.vx = existing.vx;
                        n.vy = existing.vy;
                        n.fx = existing.fx;
                        n.fy = existing.fy;
                        n.seed = existing.seed;
                    } else {
                        n.x = node.x + (Math.random() - 0.5) * 80;
                        n.y = node.y + (Math.random() - 0.5) * 80;
                        n.vx = 0;
                        n.vy = 0;
                        n.seed = Math.random() * 1000;
                    }
                    
                    if (n.label === "MindPalace") n.r = 14;
                    else if (n.label === "Page") n.r = 8;
                    else if (n.label === "Block") n.r = 5;
                    else if (n.label === "Cybernet") n.r = 13;
                    else if (n.label === "StateMachine") n.r = 10;
                    else if (n.label === "TraversalStep") n.r = 8;
                    else if (n.label === "Identity") n.r = 7;
                    else if (n.label === "ExecutionState") n.r = 6;
                    else if (n.label === "SimulationRun") n.r = 6;
                    else n.r = 5;
                    
                    updatedNodes.push(n);
                    subNodeById.set(n.id, n);
                }
            });
            
            surfacedReachableIds.forEach(id => {
                if (!subNodeById.has(id)) {
                    const existing = nodeById.get(id);
                    if (existing) {
                        updatedNodes.push(existing);
                        subNodeById.set(id, existing);
                    }
                }
            });
            
            const clickedNodeInSubgraph = subNodeById.get(node.id);
            if (clickedNodeInSubgraph) {
                clickedNodeInSubgraph.fx = clickedNodeInSubgraph.x;
                clickedNodeInSubgraph.fy = clickedNodeInSubgraph.y;
            }
            
            const updatedLinks = [];
            
            subLinks.forEach(l => {
                const src = subNodeById.get(l.source);
                const tgt = subNodeById.get(l.target);
                if (src && tgt) {
                    updatedLinks.push({
                        source: src,
                        target: tgt,
                        type: l.type
                    });
                }
            });
            
            originalLinks.forEach(link => {
                const srcId = (typeof link.source === "object") ? link.source.id : link.source;
                const tgtId = (typeof link.target === "object") ? link.target.id : link.target;
                if (subNodeById.has(srcId) && subNodeById.has(tgtId)) {
                    const exists = updatedLinks.some(l => {
                        const lSrcId = (typeof l.source === "object") ? l.source.id : l.source;
                        const lTgtId = (typeof l.target === "object") ? l.target.id : l.target;
                        return lSrcId === srcId && lTgtId === tgtId && l.type === link.type;
                    });
                    if (!exists) {
                        updatedLinks.push({
                            source: subNodeById.get(srcId),
                            target: subNodeById.get(tgtId),
                            type: link.type
                        });
                    }
                }
            });
            
            nodes = updatedNodes;
            links = updatedLinks;
            
            simulation.nodes(nodes);
            simulation.force("link").links(links);
            simulation.alpha(0.3).restart();
            
        } catch (e) {
            console.error("Error showing node subgraph:", e);
        }
    }

    function restoreFullGraph() {
        if (originalNodes && originalLinks) {
            nodes = [...originalNodes];
            links = [...originalLinks];
            
            nodes.forEach(n => {
                n.fx = null;
                n.fy = null;
            });
            
            simulation.nodes(nodes);
            simulation.force("link").links(links);
            simulation.alpha(0.3).restart();
        }
    }

    function updateSimulationDimensions() {
        if (!simulation) return;
        const W = window.innerWidth;
        const H = window.innerHeight;
        
        recalculateDynamicDistricts();
        
        simulation.force("x", d3.forceX().x(d => {
            const dist = getDistrict(d);
            return dist ? dist.x : W / 2;
        }).strength(0.18));
        
        simulation.force("y", d3.forceY().y(d => {
            const dist = getDistrict(d);
            return dist ? dist.y : H / 2;
        }).strength(0.18));
        
        simulation.alpha(0.1).restart();
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
        const node = nodes.find(n => n.name === name || n.id === name || n.label === name);
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

        simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(85).strength(0.3))
            .force("charge", d3.forceManyBody().strength(-120))
            .force("collision", d3.forceCollide().radius(22))
            .force("x", d3.forceX().x(d => {
                const dist = getDistrict(d);
                return dist ? dist.x : W / 2;
            }).strength(0.18))
            .force("y", d3.forceY().y(d => {
                const dist = getDistrict(d);
                return dist ? dist.y : H / 2;
            }).strength(0.18));
            
        // Bind zoom behavior
        zoom = d3.zoom()
            .scaleExtent([0.15, 4])
            .on("zoom", (event) => {
                currentTransform = event.transform;
            });

        // Bind drag, zoom, and click behavior directly to canvas to prevent conflict
        d3.select(canvas)
            .call(d3.drag()
                .container(canvas)
                .subject(dragsubject)
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended))
            .call(zoom)
            .on("dblclick.zoom", null)
            .on("click", (event) => {
                if (event.defaultPrevented) return;
                if (hoveredNode) {
                    selectNode(hoveredNode);
                } else {
                    deselectNode();
                }
            });
                
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
        const adjustedX = (event.x - currentTransform.x) / currentTransform.k;
        const adjustedY = (event.y - currentTransform.y) / currentTransform.k;
        for (let i = nodes.length - 1; i >= 0; i--) {
            const node = nodes[i];
            if (Math.hypot(node.x - adjustedX, node.y - adjustedY) < node.r + 8) {
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
        event.subject.fx = (event.x - currentTransform.x) / currentTransform.k;
        event.subject.fy = (event.y - currentTransform.y) / currentTransform.k;
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
        if (node.label === "MindPalace") return [6, 182, 212]; // cyan
        if (node.label === "Page") return [34, 211, 238]; // teal
        if (node.label === "Block") return [148, 163, 184]; // grey
        if (node.active_tag === "cybernet") return [46, 213, 115]; // green
        if (node.active_tag === "step") return [0, 210, 255]; // cyan
        if (node.active_tag === "state_machine") return [160, 100, 255]; // purple
        if (node.label === "ExecutionState") return [180, 255, 0]; // neon yellow/green
        
        const dist = getDistrict(node);
        if (dist && dist.color) return dist.color;
        
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
        // No-op: Background district/locale circles and labels are not rendered,
        // allowing nodes to self-organize cleanly in a pure force-directed layout.
    }

    function renderLoop(timestamp) {
        if (!ctx) return;
        
        const W = window.innerWidth;
        const H = window.innerHeight;
        const time = timestamp / 1000;
        
        ctx.clearRect(0, 0, W, H);
        
        // Draw grid fixed in screenspace for parallax layer effect
        drawGrid(ctx, W, H);
        
        ctx.save();
        ctx.translate(currentTransform.x, currentTransform.y);
        ctx.scale(currentTransform.k, currentTransform.k);
        
        drawDistricts(ctx, W, H, time);
        
        const largeGraphMode = (nodes.length > 150);
        
        // Draw links
        links.forEach(link => {
            const source = link.source;
            const target = link.target;
            if (source.x && source.y && target.x && target.y) {
                const sourceOpacity = source.highlightOpacity || 0;
                const targetOpacity = target.highlightOpacity || 0;
                const linkOpacity = Math.max(sourceOpacity, targetOpacity);
                const isActiveTransition = (linkOpacity > 0 || source.active_tag === "step" || target.active_tag === "step");

                if (largeGraphMode && !isActiveTransition) {
                    ctx.strokeStyle = "rgba(120, 120, 120, 0.05)";
                    ctx.lineWidth = 0.5;
                    ctx.beginPath();
                    ctx.moveTo(source.x, source.y);
                    ctx.lineTo(target.x, target.y);
                    ctx.stroke();
                } else {
                    const isHighlighted = linkOpacity > 0;
                    const baseAlpha = isHighlighted ? 0.06 + 0.35 * linkOpacity : 0.06;
                    const lineWidth = isHighlighted ? 0.8 + 1.2 * linkOpacity : 0.8;
                    
                    const grad = ctx.createLinearGradient(source.x, source.y, target.x, target.y);
                    const colorStart = getRGBColorString(source);
                    const colorEnd = getRGBColorString(target);
                    
                    grad.addColorStop(0, `rgba(${colorStart}, ${baseAlpha})`);
                    grad.addColorStop(1, `rgba(${colorEnd}, ${baseAlpha})`);
                    
                    ctx.strokeStyle = grad;
                    ctx.lineWidth = lineWidth;
                    ctx.beginPath();
                    ctx.moveTo(source.x, source.y);
                    ctx.lineTo(target.x, target.y);
                    ctx.stroke();
                    
                    if (isHighlighted || !largeGraphMode) {
                        const packetCount = isHighlighted ? Math.ceil(3 * linkOpacity) : 1;
                        const packetAlpha = isHighlighted ? 0.2 + 0.6 * linkOpacity : 0.25;
                        for (let j = 0; j < packetCount; j++) {
                            const offset = j / packetCount;
                            const p = (time * 0.22 + (parseInt(source.id) * 0.08 || 0) + offset) % 1.0;
                            const px = source.x + (target.x - source.x) * p;
                            const py = source.y + (target.y - source.y) * p;
                            
                            const G_flow = '01アイウエオ';
                            const charIdx = Math.floor((time * 6 + j) % G_flow.length);
                            const flowChar = G_flow[charIdx];
                            
                            ctx.fillStyle = `rgba(${colorEnd}, ${packetAlpha})`;
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
                const isActive = node.active_tag || node.highlighted || (node === hoveredNode);
                if (!largeGraphMode || isActive) {
                    const c = getRGBColor(node);
                    const opacity = node.highlightOpacity || 0;
                    const glow = node.active_tag ? 2.2 : (node.highlighted ? 0.4 + 1.4 * opacity : 0.4);
                    const act = node.active_tag === "step" ? 1.6 : (node.highlighted ? 0.1 + 0.9 * opacity : 0.1);
                    drawBloom(ctx, node.x, node.y, node.r, c, glow, act);
                }
            }
        });
        
        // Draw node orbs
        nodes.forEach(node => {
            if (node.x && node.y) {
                const c = getRGBColor(node);
                const isActive = node.active_tag || node.highlighted || (node === hoveredNode);
                
                if (largeGraphMode && !isActive) {
                    ctx.fillStyle = `rgba(${c[0]}, ${c[1]}, ${c[2]}, 0.55)`;
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, node.r * 0.8, 0, Math.PI * 2);
                    ctx.fill();
                } else {
                    const opacity = node.highlightOpacity || 0;
                    const act = node.active_tag === "step" ? 1.6 : (node.highlighted ? 0.1 + 0.9 * opacity : 0.1);
                    const glow = node.active_tag ? 2.2 : (node.highlighted ? 0.4 + 1.4 * opacity : 0.4);
                    drawOrb(ctx, node.x, node.y, node.r, c, act, glow, time, node.seed || 0, node === hoveredNode, (mouseX - currentTransform.x) / currentTransform.k, (mouseY - currentTransform.y) / currentTransform.k, node.label);
                }
            }
        });        // Draw labels, focus indicators, overlays
        nodes.forEach(node => {
            if (node.x && node.y) {
                const isHov = (node === hoveredNode);
                const isFocused = (node.highlightOpacity && node.highlightOpacity > 0) || node.highlighted;
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
                    if (node.label === "MindPalace") {
                        ctx.save();
                        ctx.translate(node.x, node.y);
                        
                        // Dotted neon-cyan orbit ring
                        ctx.strokeStyle = "rgba(6, 182, 212, 0.85)";
                        ctx.lineWidth = 1.0;
                        ctx.setLineDash([3, 5]);
                        ctx.beginPath();
                        ctx.arc(0, 0, node.r * 3.2, 0, Math.PI * 2);
                        ctx.stroke();
                        ctx.setLineDash([]); // Reset line dash
                        
                        // Solid inner ring
                        ctx.strokeStyle = "rgba(6, 182, 212, 0.3)";
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.arc(0, 0, node.r * 1.8, 0, Math.PI * 2);
                        ctx.stroke();
                        
                        ctx.restore();
                        
                        ctx.fillStyle = "rgba(6, 182, 212, 0.9)";
                        ctx.font = "bold 7px monospace";
                        ctx.textAlign = "center";
                        ctx.fillText("[MIND PALACE ISLAND]", node.x, node.y - node.r - 9);
                    } else {
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
                    }
                } else if (isFocused) {
                    const finalOpacity = node.highlightOpacity || 0.4;
                    ctx.save();
                    ctx.translate(node.x, node.y);
                    ctx.rotate(-time * 0.8 + node.seed * 0.01);
                    const ringR = node.r * 2.2;
                    ctx.strokeStyle = `rgba(180, 90, 255, ${0.85 * finalOpacity})`;
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
                    
                    ctx.fillStyle = `rgba(210, 150, 255, ${0.95 * finalOpacity})`;
                    ctx.beginPath();
                    const dotAngle = time * 2.5 + node.seed;
                    ctx.arc(node.x + Math.cos(dotAngle) * ringR, node.y + Math.sin(dotAngle) * ringR, 2.0, 0, Math.PI * 2);
                    ctx.fill();
 
                    if (finalOpacity >= 0.95) {
                        ctx.fillStyle = "rgba(210, 160, 255, 0.9)";
                        ctx.font = "bold 7px monospace";
                        ctx.textAlign = "center";
                        ctx.fillText("[AGENT FOCUS]", node.x, node.y - node.r - 8);
                    }
                } else if (node.active_tag === "step" || node.label === "Cybernet") {
                    ctx.fillStyle = "rgba(180, 210, 230, 0.7)";
                    ctx.font = "8px 'Outfit', sans-serif";
                    ctx.textAlign = "center";
                    ctx.fillText(node.name, node.x, node.y + node.r + 13);
                }
            }
        });
        
        ctx.restore();
        
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
                if (node.label === "MindPalace") node.r = 14;
                else if (node.label === "Page") node.r = 8;
                else if (node.label === "Block") node.r = 5;
                else if (node.label === "Cybernet") node.r = 13;
                else if (node.label === "StateMachine") node.r = 10;
                else if (node.label === "TraversalStep") node.r = 8;
                else if (node.label === "Identity") node.r = 7;
                else if (node.label === "ExecutionState") node.r = 6;
                else if (node.label === "SimulationRun") node.r = 6;
                else node.r = 5;
            });

            const largeGraphMode = (rawNodes.length > 150);
            const W = window.innerWidth;
            const H = window.innerHeight;

            if (largeGraphMode) {
                simulation.force("charge").strength(-15);
                simulation.force("collision").radius(6);
                simulation.force("link").distance(25).strength(0.3);
                simulation.alphaDecay(0.08);
                simulation.force("x", d3.forceX().x(d => {
                    const dist = getDistrict(d);
                    return dist ? dist.x : W / 2;
                }).strength(0.12));
                simulation.force("y", d3.forceY().y(d => {
                    const dist = getDistrict(d);
                    return dist ? dist.y : H / 2;
                }).strength(0.12));
            } else {
                simulation.force("charge").strength(-120);
                simulation.force("collision").radius(d => d.label === "Block" ? 10 : (d.label === "Page" ? 14 : 22));
                simulation.force("link").distance(70).strength(0.3);
                simulation.alphaDecay(0.0228);
                simulation.force("x", d3.forceX().x(d => {
                    const dist = getDistrict(d);
                    return dist ? dist.x : W / 2;
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
                
                // Pre-resolve domain and subdomain
                let dom = node.properties && node.properties.domain;
                let sub = node.properties && node.properties.subdomain;
                if (!dom) {
                    if (node.label === "Cybernet" || node.label === "Identity" || node.label === "Skill" ||
                        node.label === "StateMachine" || node.label === "TraversalStep" || node.label === "ExecutionTrace" ||
                        node.label === "SimulationRun" || node.label === "TraversalState" || node.label === "ExecutionState") {
                        dom = "cyberneticity";
                    } else {
                        dom = "general";
                    }
                }
                if (!sub) {
                    if (node.label) sub = node.label.toLowerCase();
                    else sub = "core";
                }
                node.resolvedDomain = dom;
                node.resolvedSubdomain = sub;
                
                if (existing) {
                    node.x = existing.x;
                    node.y = existing.y;
                    node.vx = existing.vx;
                    node.vy = existing.vy;
                    node.fx = existing.fx;
                    node.fy = existing.fy;
                    node.seed = existing.seed;
                } else {
                    node.x = window.innerWidth / 2 + (Math.random() - 0.5) * 100;
                    node.y = window.innerHeight / 2 + (Math.random() - 0.5) * 100;
                    node.vx = 0;
                    node.vy = 0;
                }
                return node;
            });

            // Recalculate dynamic districts now that nodes are resolved
            recalculateDynamicDistricts();

            // Position new nodes at their resolved district coordinates
            nodes.forEach(node => {
                const existing = existingNodes.get(node.id);
                if (!existing) {
                    const dist = getDistrict(node);
                    if (dist) {
                        node.x = dist.x + (Math.random() - 0.5) * 40;
                        node.y = dist.y + (Math.random() - 0.5) * 40;
                    }
                }
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
            
            if (!selectedNode) {
                originalNodes = [...nodes];
                originalLinks = [...links];
            }
            
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

            // Apply current focus highlights to newly fetched nodes
            nodes.forEach(node => {
                const opacity = Math.max(
                    activeFocusNodes.get(node.name) || 0,
                    activeFocusNodes.get(node.id) || 0,
                    activeFocusLabels.get(node.label) || 0
                );
                node.highlightOpacity = opacity;
                node.highlighted = opacity > 0;
            });

            simulation.alpha(0.3).restart();
            window.selectNode = selectNode;
            window.deselectNode = deselectNode;
            window.drawGraph = drawGraph;

        } catch (e) {
            console.error("D3 Draw Error:", e);
        }
    }

    async function syncActiveIdentity() {
        try {
            const res = await fetch("/api/agent_logs");
            const data = await res.json();
            
            // Recalculate focus map from history (up to 20 queries with fading relevance opacity)
            const focusMap = new Map();
            const focusLabelsMap = new Map();
            
            let queryCount = 0;
            const maxHistoricalQueries = 20;
            
            if (data.logs) {
                for (let i = data.logs.length - 1; i >= 0; i--) {
                    const log = data.logs[i];
                    const hasFocus = (log.focus_nodes && log.focus_nodes.length > 0) || (log.focus_labels && log.focus_labels.length > 0);
                    if (hasFocus) {
                        const opacity = 1.0 - (queryCount / maxHistoricalQueries);
                        
                        if (log.focus_nodes) {
                            log.focus_nodes.forEach(name => {
                                if (!focusMap.has(name) || focusMap.get(name) < opacity) {
                                    focusMap.set(name, opacity);
                                }
                            });
                        }
                        if (log.focus_labels) {
                            log.focus_labels.forEach(lbl => {
                                if (!focusLabelsMap.has(lbl) || focusLabelsMap.get(lbl) < opacity) {
                                    focusLabelsMap.set(lbl, opacity);
                                }
                            });
                        }
                        
                        queryCount++;
                        if (queryCount >= maxHistoricalQueries) {
                            break;
                        }
                    }
                }
            }

            activeFocusNodes = focusMap;
            activeFocusLabels = focusLabelsMap;

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
                    const opacity = Math.max(
                        activeFocusNodes.get(node.name) || 0,
                        activeFocusNodes.get(node.id) || 0,
                        activeFocusLabels.get(node.label) || 0
                    );
                    node.highlightOpacity = opacity;
                    node.highlighted = opacity > 0;
                });
            }
        } catch (e) {
            console.error("Failed to sync identity state:", e);
        }
    }

    // Refresh layout state every 1500ms
    const syncInterval = setInterval(syncActiveIdentity, 1500);

    // ==========================================
    // SPEC LAB FUNCTIONALITY
    // ==========================================
    const specPanel = document.getElementById("spec-panel");
    const specToggleBtn = document.getElementById("spec-lab-toggle-btn");
    const specCloseBtn = document.getElementById("spec-panel-close-btn");
    const templateSelect = document.getElementById("template-select");
    const specSelect = document.getElementById("spec-select");
    const loadTemplateBtn = document.getElementById("load-template-btn");
    const loadSpecBtn = document.getElementById("load-spec-btn");
    const specFilenameInput = document.getElementById("spec-filename");
    const specEditor = document.getElementById("spec-editor");
    const saveSpecBtn = document.getElementById("save-spec-btn");
    const copySpecBtn = document.getElementById("copy-spec-btn");
    const specStatusBar = document.getElementById("spec-status-bar");
    const specPreview = document.getElementById("spec-preview");

    const tabComposerBtn = document.getElementById("tab-composer");
    const tabPreviewBtn = document.getElementById("tab-preview");
    const composerView = document.getElementById("composer-view");
    const previewView = document.getElementById("preview-view");
    const editRawCheckbox = document.getElementById("edit-raw-mode");
    const addArgBtn = document.getElementById("add-arg-btn");

    // Spec Lab State
    let specBlocks = [];
    let specArgs = []; // array of { id, name, value }
    let specArgValues = {}; // map of name -> value

    function generateId() {
        return 'id_' + Math.random().toString(36).substr(2, 9);
    }

    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function showSpecStatus(message, isError = false) {
        if (!specStatusBar) return;
        specStatusBar.textContent = message;
        specStatusBar.className = `status-bar ${isError ? 'error' : 'success'}`;
        specStatusBar.classList.remove("hidden");
        
        setTimeout(() => {
            specStatusBar.classList.add("hidden");
        }, 3000);
    }

    // --- Parser and Compiler ---

    function isListItem(line) {
        let trimmed = line.trim();
        return trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('+ ') || /^\d+\.\s+/.test(trimmed);
    }

    function removeListBullet(line) {
        let trimmed = line.trim();
        if (/^\d+\.\s+/.test(trimmed)) {
            return trimmed.replace(/^\d+\.\s+/, '');
        }
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('+ ')) {
            return trimmed.substring(2).trim();
        }
        return trimmed;
    }

    function parseKVListItem(line) {
        let trimmed = line.trim();
        if (/^\d+\.\s+/.test(trimmed)) {
            trimmed = trimmed.replace(/^\d+\.\s+/, '');
        } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('+ ')) {
            trimmed = trimmed.substring(2).trim();
        } else {
            return null;
        }
        
        let match = trimmed.match(/^\*?\*?([^*:]+)\*?\*?\s*:\s*(.*)$/);
        if (match) {
            return {
                key: match[1].trim(),
                value: match[2].trim()
            };
        }
        return null;
    }

    function parseMarkdownToBlocks(markdown) {
        let blocks = [];
        let lines = markdown.split('\n');
        let i = 0;
        
        while (i < lines.length) {
            let line = lines[i];
            
            if (line.trim() === '') {
                i++;
                continue;
            }
            
            // Code Block
            if (line.trim().startsWith('```')) {
                let lang = line.trim().slice(3).trim();
                let codeLines = [];
                i++;
                while (i < lines.length && !lines[i].trim().startsWith('```')) {
                    codeLines.push(lines[i]);
                    i++;
                }
                blocks.push({
                    id: generateId(),
                    type: 'code',
                    lang: lang || 'text',
                    content: codeLines.join('\n')
                });
                i++;
                continue;
            }
            
            // Headers
            if (line.trim().startsWith('#')) {
                let level = 0;
                let trimmed = line.trim();
                while (trimmed.startsWith('#')) {
                    level++;
                    trimmed = trimmed.substring(1);
                }
                blocks.push({
                    id: generateId(),
                    type: 'header',
                    content: trimmed.trim(),
                    level: level
                });
                i++;
                continue;
            }
            
            // List Items
            if (isListItem(line)) {
                let items = [];
                while (i < lines.length && isListItem(lines[i])) {
                    let currentItemLine = lines[i];
                    let kv = parseKVListItem(currentItemLine);
                    
                    if (kv) {
                        if (kv.value === '|') {
                            let multilineValue = [];
                            i++;
                            while (i < lines.length && (lines[i].startsWith('  ') || lines[i].startsWith('\t') || lines[i].trim() === '')) {
                                let rawLine = lines[i];
                                if (rawLine.startsWith('  ')) {
                                    multilineValue.push(rawLine.slice(2));
                                } else if (rawLine.startsWith('\t')) {
                                    multilineValue.push(rawLine.slice(1));
                                } else {
                                    multilineValue.push(rawLine);
                                }
                                i++;
                            }
                            items.push({
                                type: 'kv_pair',
                                key: kv.key,
                                value: multilineValue.join('\n')
                            });
                        } else {
                            items.push({
                                type: 'kv_pair',
                                key: kv.key,
                                value: kv.value
                            });
                            i++;
                        }
                    } else {
                        items.push({
                            type: 'plain_item',
                            content: removeListBullet(currentItemLine)
                        });
                        i++;
                    }
                }
                
                let allKV = items.every(item => item.type === 'kv_pair');
                if (allKV && items.length > 0) {
                    blocks.push({
                        id: generateId(),
                        type: 'kv',
                        kvPairs: items.map(item => ({ key: item.key, value: item.value }))
                    });
                } else {
                    let content = items.map(item => {
                        if (item.type === 'kv_pair') {
                            return `**${item.key}**: ${item.value}`;
                        } else {
                            return item.content;
                        }
                    }).join('\n');
                    
                    blocks.push({
                        id: generateId(),
                        type: 'list',
                        content: content
                    });
                }
                continue;
            }
            
            // Plain Text
            let textLines = [];
            while (i < lines.length && lines[i].trim() !== '' && !lines[i].trim().startsWith('#') && !lines[i].trim().startsWith('```') && !isListItem(lines[i])) {
                textLines.push(lines[i]);
                i++;
            }
            if (textLines.length > 0) {
                blocks.push({
                    id: generateId(),
                    type: 'text',
                    content: textLines.join('\n')
                });
            } else {
                i++;
            }
        }
        return blocks;
    }

    function extractArgsFromMarkdown(markdown) {
        let args = new Set();
        let braceMatches = markdown.matchAll(/\$\{([a-zA-Z0-9_]+)\}/g);
        for (let match of braceMatches) {
            args.add(match[1]);
        }
        let bracketMatches = markdown.matchAll(/\[([a-zA-Z0-9_]+)\](?![\(:])/g);
        for (let match of bracketMatches) {
            args.add(match[1]);
        }
        return Array.from(args);
    }

    function compileSpecMarkdown() {
        let markdown = '';
        for (let block of specBlocks) {
            if (block.type === 'header') {
                let prefix = '#'.repeat(block.level || 1);
                markdown += `${prefix} ${block.content}\n\n`;
            } else if (block.type === 'text') {
                markdown += `${block.content}\n\n`;
            } else if (block.type === 'kv') {
                for (let pair of block.kvPairs) {
                    let key = pair.key;
                    let value = pair.value;
                    if (value.includes('\n')) {
                        let indented = value.split('\n').map(line => '  ' + line).join('\n');
                        markdown += `* **${key}**: |\n${indented}\n`;
                    } else {
                        markdown += `* **${key}**: ${value}\n`;
                    }
                }
                markdown += '\n';
            } else if (block.type === 'list') {
                let lines = block.content.split('\n');
                for (let line of lines) {
                    if (line.trim() !== '') {
                        markdown += `* ${line}\n`;
                    }
                }
                markdown += '\n';
            } else if (block.type === 'code') {
                markdown += `\`\`\`${block.lang || 'text'}\n${block.content}\n\`\`\`\n\n`;
            }
        }
        
        let compiled = markdown;
        for (let key in specArgValues) {
            let val = specArgValues[key];
            let re = new RegExp('\\$\\{' + escapeRegExp(key) + '\\}', 'g');
            compiled = compiled.replace(re, val);
            
            let reBracket = new RegExp('\\[' + escapeRegExp(key) + '\\]', 'gi');
            compiled = compiled.replace(reBracket, val);
        }
        return compiled;
    }

    // --- DOM Rendering ---

    function renderBlockWorkspace() {
        const container = document.getElementById("spec-blocks-container");
        if (!container) return;
        container.innerHTML = "";
        
        if (specBlocks.length === 0) {
            container.innerHTML = `<div class="empty-workspace-hint">No blocks in workspace. Use the Block Library above to add blocks.</div>`;
            return;
        }
        
        specBlocks.forEach((block, index) => {
            const blockEl = document.createElement("div");
            blockEl.className = `block-item block-${block.type}`;
            blockEl.dataset.id = block.id;
            
            const headerEl = document.createElement("div");
            headerEl.className = "block-item-header";
            
            const badgeEl = document.createElement("span");
            badgeEl.className = `block-type-badge badge-${block.type}`;
            badgeEl.textContent = block.type.toUpperCase();
            
            const actionsEl = document.createElement("div");
            actionsEl.className = "block-actions";
            
            const upBtn = document.createElement("button");
            upBtn.className = "block-action-btn";
            upBtn.innerHTML = "▲";
            upBtn.disabled = index === 0;
            upBtn.addEventListener("click", () => moveBlock(index, -1));
            
            const downBtn = document.createElement("button");
            downBtn.className = "block-action-btn";
            downBtn.innerHTML = "▼";
            downBtn.disabled = index === specBlocks.length - 1;
            downBtn.addEventListener("click", () => moveBlock(index, 1));
            
            const delBtn = document.createElement("button");
            delBtn.className = "block-action-btn delete";
            delBtn.innerHTML = "&times;";
            delBtn.addEventListener("click", () => deleteBlock(index));
            
            actionsEl.appendChild(upBtn);
            actionsEl.appendChild(downBtn);
            actionsEl.appendChild(delBtn);
            
            headerEl.appendChild(badgeEl);
            headerEl.appendChild(actionsEl);
            blockEl.appendChild(headerEl);
            
            const bodyEl = document.createElement("div");
            bodyEl.className = "block-item-body";
            
            if (block.type === 'header') {
                const levelSelect = document.createElement("select");
                levelSelect.className = "block-header-level";
                for (let l = 1; l <= 6; l++) {
                    const opt = document.createElement("option");
                    opt.value = l;
                    opt.textContent = `H${l}`;
                    if (block.level === l) opt.selected = true;
                    levelSelect.appendChild(opt);
                }
                levelSelect.addEventListener("change", (e) => {
                    block.level = parseInt(e.target.value);
                    updatePreview();
                });
                
                const textInput = document.createElement("input");
                textInput.type = "text";
                textInput.className = "block-header-input";
                textInput.placeholder = "Header Text...";
                textInput.value = block.content || "";
                textInput.addEventListener("input", (e) => {
                    block.content = e.target.value;
                    updatePreview();
                });
                
                const row = document.createElement("div");
                row.className = "block-header-row";
                row.appendChild(levelSelect);
                row.appendChild(textInput);
                bodyEl.appendChild(row);
                
            } else if (block.type === 'text') {
                const textarea = document.createElement("textarea");
                textarea.className = "block-textarea text-block-textarea";
                textarea.placeholder = "Write prose text here...";
                textarea.value = block.content || "";
                textarea.addEventListener("input", (e) => {
                    block.content = e.target.value;
                    updatePreview();
                });
                bodyEl.appendChild(textarea);
                
            } else if (block.type === 'kv') {
                const kvContainer = document.createElement("div");
                kvContainer.className = "block-kv-container";
                
                function renderKVPairs() {
                    kvContainer.innerHTML = "";
                    block.kvPairs.forEach((pair, pairIdx) => {
                        const row = document.createElement("div");
                        row.className = "block-kv-row";
                        
                        const keyInput = document.createElement("input");
                        keyInput.type = "text";
                        keyInput.className = "block-kv-key";
                        keyInput.placeholder = "Key";
                        keyInput.value = pair.key || "";
                        keyInput.addEventListener("input", (e) => {
                            pair.key = e.target.value;
                            updatePreview();
                        });
                        
                        const valInput = document.createElement("textarea");
                        valInput.className = "block-kv-val";
                        valInput.placeholder = "Value";
                        valInput.value = pair.value || "";
                        valInput.rows = pair.value.includes('\n') ? pair.value.split('\n').length : 1;
                        valInput.addEventListener("input", (e) => {
                            pair.value = e.target.value;
                            valInput.rows = e.target.value.includes('\n') ? e.target.value.split('\n').length : 1;
                            updatePreview();
                        });
                        
                        const removePairBtn = document.createElement("button");
                        removePairBtn.className = "block-kv-remove";
                        removePairBtn.innerHTML = "&times;";
                        removePairBtn.addEventListener("click", () => {
                            block.kvPairs.splice(pairIdx, 1);
                            renderKVPairs();
                            updatePreview();
                        });
                        
                        row.appendChild(keyInput);
                        row.appendChild(valInput);
                        row.appendChild(removePairBtn);
                        kvContainer.appendChild(row);
                    });
                    
                    const addPairBtn = document.createElement("button");
                    addPairBtn.className = "spec-btn compact block-kv-add-btn";
                    addPairBtn.textContent = "+ Add Row";
                    addPairBtn.addEventListener("click", () => {
                        block.kvPairs.push({ key: "", value: "" });
                        renderKVPairs();
                        updatePreview();
                    });
                    kvContainer.appendChild(addPairBtn);
                }
                
                renderKVPairs();
                bodyEl.appendChild(kvContainer);
                
            } else if (block.type === 'list') {
                const textarea = document.createElement("textarea");
                textarea.className = "block-textarea list-block-textarea";
                textarea.placeholder = "Enter each bullet item on a new line...";
                textarea.value = block.content || "";
                textarea.addEventListener("input", (e) => {
                    block.content = e.target.value;
                    updatePreview();
                });
                bodyEl.appendChild(textarea);
                
            } else if (block.type === 'code') {
                const langSelect = document.createElement("select");
                langSelect.className = "block-code-lang";
                const languages = ["text", "javascript", "yaml", "json", "cypher", "python", "html", "css"];
                languages.forEach(l => {
                    const opt = document.createElement("option");
                    opt.value = l;
                    opt.textContent = l;
                    if (block.lang === l) opt.selected = true;
                    langSelect.appendChild(opt);
                });
                langSelect.addEventListener("change", (e) => {
                    block.lang = e.target.value;
                    updatePreview();
                });
                
                const textarea = document.createElement("textarea");
                textarea.className = "block-textarea code-block-textarea";
                textarea.placeholder = "Write source code here...";
                textarea.value = block.content || "";
                textarea.addEventListener("input", (e) => {
                    block.content = e.target.value;
                    updatePreview();
                });
                
                const row = document.createElement("div");
                row.className = "block-code-row";
                row.appendChild(langSelect);
                row.appendChild(textarea);
                bodyEl.appendChild(row);
            }
            
            blockEl.appendChild(bodyEl);
            container.appendChild(blockEl);
        });
    }

    function renderArgsList() {
        const container = document.getElementById("spec-args-container");
        if (!container) return;
        container.innerHTML = "";
        
        if (specArgs.length === 0) {
            container.innerHTML = `<div class="empty-args-hint">No arguments defined.</div>`;
            return;
        }
        
        specArgs.forEach((arg, idx) => {
            const row = document.createElement("div");
            row.className = "arg-row";
            
            const nameInput = document.createElement("input");
            nameInput.type = "text";
            nameInput.className = "arg-name-input";
            nameInput.placeholder = "Name (e.g. name)";
            nameInput.value = arg.name || "";
            nameInput.addEventListener("input", (e) => {
                const oldName = arg.name;
                const newName = e.target.value.trim();
                arg.name = newName;
                
                if (oldName !== newName) {
                    specArgValues[newName] = specArgValues[oldName] || arg.value || "";
                    delete specArgValues[oldName];
                }
                updatePreview();
            });
            
            const valInput = document.createElement("input");
            valInput.type = "text";
            valInput.className = "arg-val-input";
            valInput.placeholder = "Value";
            valInput.value = arg.value || "";
            valInput.addEventListener("input", (e) => {
                arg.value = e.target.value;
                if (arg.name) {
                    specArgValues[arg.name] = e.target.value;
                }
                updatePreview();
            });
            
            const removeBtn = document.createElement("button");
            removeBtn.className = "arg-remove-btn";
            removeBtn.innerHTML = "&times;";
            removeBtn.addEventListener("click", () => {
                if (arg.name) {
                    delete specArgValues[arg.name];
                }
                specArgs.splice(idx, 1);
                renderArgsList();
                updatePreview();
            });
            
            row.appendChild(nameInput);
            row.appendChild(valInput);
            row.appendChild(removeBtn);
            container.appendChild(row);
        });
    }

    function updatePreview() {
        const compiledMarkdown = compileSpecMarkdown();
        if (specEditor && !editRawCheckbox.checked) {
            specEditor.value = compiledMarkdown;
        }
        if (specPreview) {
            specPreview.textContent = compiledMarkdown;
        }
    }

    // --- Block Actions ---

    function addBlock(type) {
        let newBlock = { id: generateId(), type: type };
        if (type === 'header') {
            newBlock.content = "";
            newBlock.level = 2;
        } else if (type === 'text') {
            newBlock.content = "";
        } else if (type === 'kv') {
            newBlock.kvPairs = [{ key: "", value: "" }];
        } else if (type === 'list') {
            newBlock.content = "";
        } else if (type === 'code') {
            newBlock.lang = "text";
            newBlock.content = "";
        }
        
        specBlocks.push(newBlock);
        renderBlockWorkspace();
        updatePreview();
    }

    function moveBlock(index, direction) {
        let targetIndex = index + direction;
        if (targetIndex < 0 || targetIndex >= specBlocks.length) return;
        
        let temp = specBlocks[index];
        specBlocks[index] = specBlocks[targetIndex];
        specBlocks[targetIndex] = temp;
        
        renderBlockWorkspace();
        updatePreview();
    }

    function deleteBlock(index) {
        specBlocks.splice(index, 1);
        renderBlockWorkspace();
        updatePreview();
    }

    // Initialize default blocks
    specBlocks = [
        { id: generateId(), type: 'header', content: 'New Specification', level: 1 },
        { id: generateId(), type: 'text', content: 'Describe the purpose here.' }
    ];
    renderBlockWorkspace();
    renderArgsList();
    updatePreview();

    // --- Bind DOM Listeners ---

    document.querySelectorAll(".add-block-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const type = btn.getAttribute("data-type");
            addBlock(type);
        });
    });

    if (addArgBtn) {
        addArgBtn.addEventListener("click", () => {
            specArgs.push({ id: generateId(), name: "", value: "" });
            renderArgsList();
            updatePreview();
        });
    }

    if (editRawCheckbox) {
        editRawCheckbox.addEventListener("change", () => {
            if (editRawCheckbox.checked) {
                specEditor.classList.remove("hidden");
                specPreview.classList.add("hidden");
                specEditor.value = compileSpecMarkdown();
            } else {
                specEditor.classList.add("hidden");
                specPreview.classList.remove("hidden");
                
                // Parse raw text back into blocks
                const rawContent = specEditor.value;
                specBlocks = parseMarkdownToBlocks(rawContent);
                
                const extractedNames = extractArgsFromMarkdown(rawContent);
                specArgs = extractedNames.map(name => {
                    let val = specArgValues[name] || "";
                    return { id: generateId(), name: name, value: val };
                });
                specArgValues = {};
                specArgs.forEach(arg => {
                    if (arg.name) {
                        specArgValues[arg.name] = arg.value;
                    }
                });
                
                renderBlockWorkspace();
                renderArgsList();
                updatePreview();
            }
        });
    }

    if (specEditor) {
        specEditor.addEventListener("input", () => {
            if (editRawCheckbox.checked) {
                if (specPreview) {
                    specPreview.textContent = specEditor.value;
                }
            }
        });
    }

    if (tabComposerBtn && tabPreviewBtn && composerView && previewView) {
        tabComposerBtn.addEventListener("click", () => {
            tabComposerBtn.classList.add("active");
            tabPreviewBtn.classList.remove("active");
            composerView.classList.remove("hidden");
            previewView.classList.add("hidden");
            
            if (editRawCheckbox.checked) {
                const rawContent = specEditor.value;
                specBlocks = parseMarkdownToBlocks(rawContent);
                
                const extractedNames = extractArgsFromMarkdown(rawContent);
                specArgs = extractedNames.map(name => {
                    let val = specArgValues[name] || "";
                    return { id: generateId(), name: name, value: val };
                });
                specArgValues = {};
                specArgs.forEach(arg => {
                    if (arg.name) {
                        specArgValues[arg.name] = arg.value;
                    }
                });
                
                renderBlockWorkspace();
                renderArgsList();
            }
            updatePreview();
        });
        
        tabPreviewBtn.addEventListener("click", () => {
            tabPreviewBtn.classList.add("active");
            tabComposerBtn.classList.remove("active");
            previewView.classList.remove("hidden");
            composerView.classList.add("hidden");
            updatePreview();
        });
    }

    if (specToggleBtn && specPanel) {
        specToggleBtn.addEventListener("click", () => {
            specPanel.classList.toggle("open");
            if (specPanel.classList.contains("open")) {
                loadTemplatesAndSpecs();
            }
        });
    }

    if (specCloseBtn && specPanel) {
        specCloseBtn.addEventListener("click", () => {
            specPanel.classList.remove("open");
        });
    }

    async function loadTemplatesAndSpecs() {
        if (!templateSelect || !specSelect) return;
        try {
            // Load templates list
            const tRes = await fetch("/api/specs/templates");
            if (tRes.ok) {
                const tData = await tRes.json();
                templateSelect.innerHTML = '<option value="">-- Select Template --</option>';
                tData.templates.forEach(t => {
                    const opt = document.createElement("option");
                    opt.value = t;
                    opt.textContent = t.replace("_template.md", "").toUpperCase().replace(/_/g, " ");
                    templateSelect.appendChild(opt);
                });
            }

            // Load saved specs list
            const sRes = await fetch("/api/specs/list");
            if (sRes.ok) {
                const sData = await sRes.json();
                specSelect.innerHTML = '<option value="">-- Select Saved Spec --</option>';
                sData.specs.forEach(s => {
                    const opt = document.createElement("option");
                    opt.value = s;
                    opt.textContent = s;
                    specSelect.appendChild(opt);
                });
            }
        } catch (err) {
            console.error("Failed to load templates or specs list:", err);
        }
    }

    if (loadTemplateBtn && templateSelect && specFilenameInput) {
        loadTemplateBtn.addEventListener("click", async () => {
            const filename = templateSelect.value;
            if (!filename) {
                showSpecStatus("Please select a template to load.", true);
                return;
            }
            try {
                const res = await fetch(`/api/specs/template/read?filename=${encodeURIComponent(filename)}`);
                if (res.ok) {
                    const data = await res.json();
                    const content = data.content;
                    
                    specBlocks = parseMarkdownToBlocks(content);
                    const extractedNames = extractArgsFromMarkdown(content);
                    specArgs = extractedNames.map(name => {
                        let val = specArgValues[name] || "";
                        return { id: generateId(), name: name, value: val };
                    });
                    specArgValues = {};
                    specArgs.forEach(arg => {
                        if (arg.name) {
                            specArgValues[arg.name] = arg.value;
                        }
                    });
                    
                    specFilenameInput.value = filename.replace("_template", "_custom");
                    
                    renderBlockWorkspace();
                    renderArgsList();
                    updatePreview();
                    
                    showSpecStatus("Template loaded and parsed.");
                } else {
                    showSpecStatus("Failed to load template content.", true);
                }
            } catch (err) {
                showSpecStatus("Error: " + err.message, true);
            }
        });
    }

    if (loadSpecBtn && specSelect && specFilenameInput) {
        loadSpecBtn.addEventListener("click", async () => {
            const filename = specSelect.value;
            if (!filename) {
                showSpecStatus("Please select a saved specification to load.", true);
                return;
            }
            try {
                const res = await fetch(`/api/specs/read?filename=${encodeURIComponent(filename)}`);
                if (res.ok) {
                    const data = await res.json();
                    const content = data.content;
                    
                    specBlocks = parseMarkdownToBlocks(content);
                    const extractedNames = extractArgsFromMarkdown(content);
                    specArgs = extractedNames.map(name => {
                        let val = specArgValues[name] || "";
                        return { id: generateId(), name: name, value: val };
                    });
                    specArgValues = {};
                    specArgs.forEach(arg => {
                        if (arg.name) {
                            specArgValues[arg.name] = arg.value;
                        }
                    });
                    
                    specFilenameInput.value = filename;
                    
                    renderBlockWorkspace();
                    renderArgsList();
                    updatePreview();
                    
                    showSpecStatus("Specification loaded and parsed.");
                } else {
                    showSpecStatus("Failed to load specification content.", true);
                }
            } catch (err) {
                showSpecStatus("Error: " + err.message, true);
            }
        });
    }

    if (saveSpecBtn && specFilenameInput) {
        saveSpecBtn.addEventListener("click", async () => {
            const filename = specFilenameInput.value.trim();
            const content = editRawCheckbox.checked ? specEditor.value : compileSpecMarkdown();
            
            if (!filename) {
                showSpecStatus("Filename is required to save.", true);
                return;
            }
            if (!filename.endsWith(".md") && !filename.endsWith(".json")) {
                showSpecStatus("Filename must end with .md or .json", true);
                return;
            }
            
            try {
                const res = await fetch("/api/specs/save", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ filename, content })
                });
                
                if (res.ok) {
                    showSpecStatus("Specification saved successfully!");
                    loadTemplatesAndSpecs();
                } else {
                    const errData = await res.json();
                    showSpecStatus("Save failed: " + (errData.detail || "Unknown error"), true);
                }
            } catch (err) {
                showSpecStatus("Save error: " + err.message, true);
            }
        });
    }

    if (copySpecBtn) {
        copySpecBtn.addEventListener("click", () => {
            const content = editRawCheckbox.checked ? specEditor.value : compileSpecMarkdown();
            if (!content) {
                showSpecStatus("No content to copy.", true);
                return;
            }
            
            navigator.clipboard.writeText(content).then(() => {
                showSpecStatus("Copied to clipboard!");
            }).catch(err => {
                showSpecStatus("Copy failed: " + err.message, true);
            });
        });
    }

    // ==========================================
    // MIND PALACE WORKSPACE
    // ==========================================
    let mindPalaces = [];
    let currentPalaceId = null;
    let currentPages = [];
    let currentPageId = null;
    let currentPageBlocks = [];

    // Tabs logic
    const tabSpecLab = document.getElementById("wk-tab-speclab");
    const tabMindPalace = document.getElementById("wk-tab-mindpalace");
    const speclabWorkspace = document.getElementById("speclab-workspace");
    const mindpalaceWorkspace = document.getElementById("mindpalace-workspace");

    if (tabSpecLab && tabMindPalace && speclabWorkspace && mindpalaceWorkspace) {
        tabSpecLab.addEventListener("click", () => {
            tabSpecLab.classList.add("active");
            tabMindPalace.classList.remove("active");
            speclabWorkspace.classList.remove("hidden");
            mindpalaceWorkspace.classList.add("hidden");
        });

        tabMindPalace.addEventListener("click", () => {
            tabMindPalace.classList.add("active");
            tabSpecLab.classList.remove("active");
            mindpalaceWorkspace.classList.remove("hidden");
            speclabWorkspace.classList.add("hidden");
            loadMindPalaces();
        });
    }

    async function loadMindPalaces() {
        try {
            const res = await fetch("/api/mindpalaces");
            const data = await res.json();
            mindPalaces = data.mindpalaces || [];
            
            const select = document.getElementById("palace-select");
            if (select) {
                const prevVal = select.value;
                select.innerHTML = '<option value="">-- Select Palace --</option>';
                mindPalaces.forEach(mp => {
                    const opt = document.createElement("option");
                    opt.value = mp.id;
                    opt.textContent = mp.name;
                    select.appendChild(opt);
                });
                if (prevVal && mindPalaces.some(m => m.id === prevVal)) {
                    select.value = prevVal;
                } else {
                    select.value = "";
                }
            }
        } catch (e) {
            console.error("Failed to load mind palaces:", e);
        }
    }

    const palaceSelect = document.getElementById("palace-select");
    if (palaceSelect) {
        palaceSelect.addEventListener("change", (e) => {
            currentPalaceId = e.target.value;
            if (currentPalaceId) {
                loadPalacePages(currentPalaceId);
            } else {
                document.getElementById("palace-pages-list").innerHTML = "";
                hidePageEditor();
            }
        });
    }

    async function loadPalacePages(mpId) {
        try {
            const res = await fetch(`/api/mindpalace/${mpId}/pages`);
            const data = await res.json();
            currentPages = data.pages || [];
            
            const list = document.getElementById("palace-pages-list");
            if (list) {
                list.innerHTML = "";
                if (currentPages.length === 0) {
                    list.innerHTML = '<div style="font-size:11px; color:var(--text-muted); padding:5px 0;">No pages yet.</div>';
                } else {
                    currentPages.forEach(p => {
                        const item = document.createElement("div");
                        item.className = "tree-item";
                        if (p.page_id === currentPageId) {
                            item.classList.add("active");
                        }
                        item.textContent = p.title;
                        item.onclick = () => {
                            Array.from(list.getElementsByClassName("tree-item")).forEach(el => el.classList.remove("active"));
                            item.classList.add("active");
                            loadPage(p.page_id);
                        };
                        list.appendChild(item);
                    });
                }
            }
        } catch (e) {
            console.error("Failed to load pages:", e);
        }
    }

    async function loadPage(pageId) {
        try {
            currentPageId = pageId;
            const res = await fetch(`/api/mindpalace/page/${pageId}`);
            const data = await res.json();
            
            document.getElementById("no-page-selected").classList.add("hidden");
            document.getElementById("page-editor-container").classList.remove("hidden");
            
            const titleInput = document.getElementById("mp-page-title");
            titleInput.value = data.title || "";
            
            currentPageBlocks = data.blocks || [];
            
            renderMpBlocks();
            compileMpPreview();
        } catch (e) {
            console.error("Failed to load page:", e);
        }
    }

    function hidePageEditor() {
        currentPageId = null;
        currentPageBlocks = [];
        const editorContainer = document.getElementById("page-editor-container");
        const placeholder = document.getElementById("no-page-selected");
        if (editorContainer) editorContainer.classList.add("hidden");
        if (placeholder) placeholder.classList.remove("hidden");
    }

    const createPalaceBtn = document.getElementById("create-palace-btn");
    if (createPalaceBtn) {
        createPalaceBtn.addEventListener("click", async () => {
            const input = document.getElementById("new-palace-name");
            const name = input.value.trim();
            if (!name) return;
            
            try {
                const res = await fetch("/api/mindpalace", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name: name })
                });
                if (res.ok) {
                    input.value = "";
                    await loadMindPalaces();
                    showSpecStatus("Palace created!");
                } else {
                    const err = await res.json();
                    showSpecStatus("Error: " + err.detail, true);
                }
            } catch(e) {
                showSpecStatus("Network error", true);
            }
        });
    }

    const createPageBtn = document.getElementById("create-page-btn");
    if (createPageBtn) {
        createPageBtn.addEventListener("click", async () => {
            const input = document.getElementById("new-page-title");
            const title = input.value.trim();
            if (!title) return;
            if (!currentPalaceId) {
                showSpecStatus("Please select a Palace first.", true);
                return;
            }
            
            try {
                const res = await fetch(`/api/mindpalace/${currentPalaceId}/page`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ title: title })
                });
                if (res.ok) {
                    const pageData = await res.json();
                    input.value = "";
                    await loadPalacePages(currentPalaceId);
                    loadPage(pageData.page_id);
                    await drawGraph(activeIdentity);
                    showSpecStatus("Page created!");
                } else {
                    const err = await res.json();
                    showSpecStatus("Error: " + err.detail, true);
                }
            } catch(e) {
                showSpecStatus("Network error", true);
            }
        });
    }

    function renderMpBlocks() {
        const container = document.getElementById("mp-blocks-container");
        if (!container) return;
        container.innerHTML = "";
        
        currentPageBlocks.forEach((block, idx) => {
            const blockEl = document.createElement("div");
            blockEl.className = "workspace-block";
            blockEl.dataset.index = idx;
            
            let color = "#cbd5e1";
            if (block.type === "header") color = "#60a5fa";
            else if (block.type === "text") color = "#fbbf24";
            else if (block.type === "kv") color = "#4ade80";
            else if (block.type === "list") color = "#f472b6";
            else if (block.type === "code") color = "#a78bfa";
            blockEl.style.borderLeftColor = color;
            
            const header = document.createElement("div");
            header.className = "block-header";
            
            const title = document.createElement("span");
            title.className = "block-title";
            title.textContent = block.type.toUpperCase();
            
            const controls = document.createElement("div");
            controls.className = "block-controls";
            
            const upBtn = document.createElement("button");
            upBtn.className = "block-ctrl-btn";
            upBtn.textContent = "↑";
            upBtn.disabled = idx === 0;
            upBtn.onclick = () => {
                const temp = currentPageBlocks[idx];
                currentPageBlocks[idx] = currentPageBlocks[idx - 1];
                currentPageBlocks[idx - 1] = temp;
                renderMpBlocks();
                compileMpPreview();
            };
            
            const downBtn = document.createElement("button");
            downBtn.className = "block-ctrl-btn";
            downBtn.textContent = "↓";
            downBtn.disabled = idx === currentPageBlocks.length - 1;
            downBtn.onclick = () => {
                const temp = currentPageBlocks[idx];
                currentPageBlocks[idx] = currentPageBlocks[idx + 1];
                currentPageBlocks[idx + 1] = temp;
                renderMpBlocks();
                compileMpPreview();
            };
            
            const delBtn = document.createElement("button");
            delBtn.className = "block-ctrl-btn del";
            delBtn.textContent = "×";
            delBtn.onclick = () => {
                currentPageBlocks.splice(idx, 1);
                renderMpBlocks();
                compileMpPreview();
            };
            
            controls.appendChild(upBtn);
            controls.appendChild(downBtn);
            controls.appendChild(delBtn);
            header.appendChild(title);
            header.appendChild(controls);
            blockEl.appendChild(header);
            
            const fields = document.createElement("div");
            fields.className = "block-fields";
            
            if (block.type === "header") {
                const row = document.createElement("div");
                row.className = "block-field-row";
                
                const select = document.createElement("select");
                select.className = "block-select";
                for (let h = 1; h <= 6; h++) {
                    const opt = document.createElement("option");
                    opt.value = h;
                    opt.textContent = `H${h}`;
                    select.appendChild(opt);
                }
                select.value = block.level || 1;
                select.onchange = (e) => {
                    block.level = parseInt(e.target.value);
                    compileMpPreview();
                };
                
                const input = document.createElement("input");
                input.className = "block-input";
                input.type = "text";
                input.value = block.content || "";
                input.placeholder = "Heading Text";
                input.oninput = (e) => {
                    block.content = e.target.value;
                    compileMpPreview();
                };
                
                row.appendChild(select);
                row.appendChild(input);
                fields.appendChild(row);
            } else if (block.type === "text") {
                const textarea = document.createElement("textarea");
                textarea.className = "block-textarea";
                textarea.value = block.content || "";
                textarea.placeholder = "Enter text paragraphs...";
                textarea.oninput = (e) => {
                    block.content = e.target.value;
                    compileMpPreview();
                };
                fields.appendChild(textarea);
            } else if (block.type === "kv") {
                const listContainer = document.createElement("div");
                listContainer.className = "block-kv-list";
                
                let pairs = [];
                try {
                    pairs = JSON.parse(block.content);
                } catch(e) {
                    pairs = [];
                }
                if (!Array.isArray(pairs)) pairs = [];
                
                function updateKvContent() {
                    block.content = JSON.stringify(pairs);
                    compileMpPreview();
                }
                
                function renderPairs() {
                    listContainer.innerHTML = "";
                    pairs.forEach((pair, pIdx) => {
                        const pairRow = document.createElement("div");
                        pairRow.className = "kv-pair-row";
                        
                        const kInput = document.createElement("input");
                        kInput.type = "text";
                        kInput.className = "kv-key-input";
                        kInput.value = pair.key || "";
                        kInput.placeholder = "Key";
                        kInput.oninput = (e) => {
                            pair.key = e.target.value;
                            updateKvContent();
                        };
                        
                        const vInput = document.createElement("input");
                        vInput.type = "text";
                        vInput.className = "kv-value-input";
                        vInput.value = pair.value || "";
                        vInput.placeholder = "Value";
                        vInput.oninput = (e) => {
                            pair.value = e.target.value;
                            updateKvContent();
                        };
                        
                        const rBtn = document.createElement("button");
                        rBtn.className = "pair-remove-btn";
                        rBtn.textContent = "×";
                        rBtn.onclick = () => {
                            pairs.splice(pIdx, 1);
                            renderPairs();
                            updateKvContent();
                        };
                        
                        pairRow.appendChild(kInput);
                        pairRow.appendChild(vInput);
                        pairRow.appendChild(rBtn);
                        listContainer.appendChild(pairRow);
                    });
                    
                    const addPairBtn = document.createElement("button");
                    addPairBtn.className = "spec-btn compact";
                    addPairBtn.textContent = "+ Add Pair";
                    addPairBtn.onclick = () => {
                        pairs.push({key: "", value: ""});
                        renderPairs();
                        updateKvContent();
                    };
                    listContainer.appendChild(addPairBtn);
                }
                renderPairs();
                fields.appendChild(listContainer);
            } else if (block.type === "list") {
                const textarea = document.createElement("textarea");
                textarea.className = "block-textarea";
                textarea.value = block.content || "";
                textarea.placeholder = "Enter list items, one per line...";
                textarea.oninput = (e) => {
                    block.content = e.target.value;
                    compileMpPreview();
                };
                fields.appendChild(textarea);
            } else if (block.type === "code") {
                const row = document.createElement("div");
                row.className = "block-field-row";
                
                const langSelect = document.createElement("select");
                langSelect.className = "block-select";
                const languages = ["text", "cypher", "javascript", "python", "json", "yaml", "markdown"];
                languages.forEach(l => {
                    const opt = document.createElement("option");
                    opt.value = l;
                    opt.textContent = l.toUpperCase();
                    langSelect.appendChild(opt);
                });
                langSelect.value = block.language || "text";
                langSelect.onchange = (e) => {
                    block.language = e.target.value;
                    compileMpPreview();
                };
                row.appendChild(langSelect);
                fields.appendChild(row);
                
                const textarea = document.createElement("textarea");
                textarea.className = "block-textarea code-font";
                textarea.value = block.content || "";
                textarea.placeholder = "Write code here...";
                textarea.oninput = (e) => {
                    block.content = e.target.value;
                    compileMpPreview();
                };
                fields.appendChild(textarea);
            }
            
            blockEl.appendChild(fields);
            container.appendChild(blockEl);
        });
    }

    function compileMpPreview() {
        const preview = document.getElementById("mp-wiki-preview");
        if (!preview) return;
        
        let html = "";
        currentPageBlocks.forEach(block => {
            if (block.type === "header") {
                const lvl = block.level || 1;
                html += `<h${lvl}>${block.content || ""}</h${lvl}>`;
            } else if (block.type === "text") {
                const text = block.content || "";
                const paras = text.split("\n\n").map(p => `<p>${p.replace(/\n/g, "<br/>")}</p>`).join("");
                html += paras;
            } else if (block.type === "kv") {
                let pairs = [];
                try {
                    pairs = JSON.parse(block.content);
                } catch(e) { pairs = []; }
                if (Array.isArray(pairs) && pairs.length > 0) {
                    html += `<table style="width:100%; border-collapse:collapse; margin:8px 0; border:1px solid rgba(255,255,255,0.05);">`;
                    pairs.forEach(p => {
                        html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                            <td style="padding:6px; font-weight:600; color:var(--neon-cyan); width:30%;">${p.key || ""}</td>
                            <td style="padding:6px; color:var(--text-secondary);">${p.value || ""}</td>
                        </tr>`;
                    });
                    html += `</table>`;
                }
            } else if (block.type === "list") {
                const text = block.content || "";
                const items = text.split("\n").filter(line => line.trim().length > 0);
                if (items.length > 0) {
                    html += `<ul style="padding-left: 20px; margin: 8px 0;">`;
                    items.forEach(it => {
                        html += `<li style="margin: 4px 0;">${it}</li>`;
                    });
                    html += `</ul>`;
                }
            } else if (block.type === "code") {
                html += `<pre style="background:rgba(0,0,0,0.35); padding:8px; border-radius:4px; font-family:monospace; margin:8px 0; overflow-x:auto;"><code>${block.content || ""}</code></pre>`;
            }
        });
        
        preview.innerHTML = html || "<p style='color:var(--text-muted); font-style:italic;'>No page blocks declared yet.</p>";
    }

    const addMpBlockBtns = document.getElementsByClassName("add-mp-block-btn");
    Array.from(addMpBlockBtns).forEach(btn => {
        btn.addEventListener("click", (e) => {
            const type = e.target.dataset.type;
            let blockContent = "";
            if (type === "kv") blockContent = "[]";
            
            currentPageBlocks.push({
                type: type,
                content: blockContent,
                level: 1,
                language: "text"
            });
            renderMpBlocks();
            compileMpPreview();
        });
    });

    const saveMpPageBtn = document.getElementById("save-mp-page-btn");
    if (saveMpPageBtn) {
        saveMpPageBtn.addEventListener("click", async () => {
            if (!currentPageId) return;
            
            try {
                const resBlocks = await fetch(`/api/mindpalace/page/${currentPageId}/blocks`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ blocks: currentPageBlocks })
                });
                
                if (resBlocks.ok) {
                    showSpecStatus("Page saved to graph!");
                    await drawGraph(activeIdentity);
                } else {
                    const err = await resBlocks.json();
                    showSpecStatus("Error: " + err.detail, true);
                }
            } catch(e) {
                showSpecStatus("Network error", true);
            }
        });
    }

    const deleteMpPageBtn = document.getElementById("delete-mp-page-btn");
    if (deleteMpPageBtn) {
        deleteMpPageBtn.addEventListener("click", async () => {
            if (!currentPageId) return;
            if (!confirm("Are you sure you want to delete this page and all its blocks?")) return;
            
            try {
                const res = await fetch(`/api/mindpalace/page/${currentPageId}`, {
                    method: "DELETE"
                });
                if (res.ok) {
                    hidePageEditor();
                    await loadPalacePages(currentPalaceId);
                    await drawGraph(activeIdentity);
                    showSpecStatus("Page deleted.");
                } else {
                    const err = await res.json();
                    showSpecStatus("Error: " + err.detail, true);
                }
            } catch(e) {
                showSpecStatus("Network error", true);
            }
        });
    }

    const exportPalaceBtn = document.getElementById("export-palace-btn");
    if (exportPalaceBtn) {
        exportPalaceBtn.addEventListener("click", async () => {
            if (!currentPalaceId) {
                showSpecStatus("Please select a Palace to export.", true);
                return;
            }
            try {
                const res = await fetch(`/api/mindpalace/${currentPalaceId}/export`, {
                    method: "POST"
                });
                if (res.ok) {
                    const data = await res.json();
                    const jsonStr = JSON.stringify(data, null, 2);
                    const blob = new Blob([jsonStr], { type: "application/json" });
                    const url = URL.createObjectURL(blob);
                    
                    const a = document.createElement("a");
                    a.href = url;
                    const palaceName = mindPalaces.find(m => m.id === currentPalaceId)?.name || "palace";
                    a.download = `${palaceName.toLowerCase().replace(/\s+/g, "_")}_mindpalace.json`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    
                    showSpecStatus("Palace exported successfully!");
                } else {
                    const err = await res.json();
                    showSpecStatus("Export failed: " + err.detail, true);
                }
            } catch(e) {
                showSpecStatus("Export error", true);
            }
        });
    }

    const importFile = document.getElementById("import-palace-file");
    if (importFile) {
        importFile.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = async (evt) => {
                try {
                    const payload = JSON.parse(evt.target.result);
                    const res = await fetch("/api/mindpalace/import", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                    });
                    if (res.ok) {
                        showSpecStatus("Palace imported successfully!");
                        await loadMindPalaces();
                        await drawGraph(activeIdentity);
                    } else {
                        const err = await res.json();
                        showSpecStatus("Import failed: " + err.detail, true);
                    }
                } catch(err) {
                    showSpecStatus("Import parse error: " + err.message, true);
                }
            };
            reader.readAsText(file);
            importFile.value = "";
        });
    }

    // Initial load on script execution
    loadTemplatesAndSpecs();

    window.addEventListener("beforeunload", () => {
        clearInterval(syncInterval);
    });
});
