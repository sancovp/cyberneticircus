// CybernetiCircus Dashboard Controller
// Interacts with /api/ endpoints to run the game loop and render status.

document.addEventListener("DOMContentLoaded", () => {
    // D3 Graph Visualizer variables
    let canvas, ctx, simulation;
    let nodes = [];
    let links = [];
    let hoveredNode = null;
    let mouseX = 0, mouseY = 0;
    const width = 600;
    const height = 300;

    // DOM Elements
    const dbStatus = document.getElementById("db-status-indicator");
    const selectCybernet = document.getElementById("cybernet-select");
    const selectStateMachine = document.getElementById("state-machine-select");
    const activeStats = document.getElementById("active-stats-container");
    const placeholder = document.getElementById("no-identity-placeholder");
    const arenaContent = document.getElementById("arena-content");
    const terminalOutput = document.getElementById("terminal-output");
    
    // Stats elements
    const statModel = document.getElementById("stat-model");
    const statFitness = document.getElementById("stat-fitness");
    const statTokens = document.getElementById("stat-tokens");
    const statCost = document.getElementById("stat-cost");
    
    // Arena elements
    const activeSmName = document.getElementById("active-sm-name");
    const activeStepId = document.getElementById("active-step-id");
    const activeStepText = document.getElementById("active-step-text");
    const callStackContainer = document.getElementById("call-stack-container");
    const callStackFrames = document.getElementById("call-stack-frames");
    const phaseBadge = document.getElementById("phase-badge");
    const tickBtn = document.getElementById("tick-compiler-btn");
    
    // Simulation history elements
    const simulationPlaceholder = document.getElementById("no-simulation-placeholder");
    const simulationTableWrapper = document.getElementById("simulation-table-wrapper");
    const simulationHistoryList = document.getElementById("simulation-history-list");

    // Modal drawer elements
    const openCreateBtn = document.getElementById("open-create-btn");
    const closeCreateBtn = document.getElementById("close-create-btn");
    const cancelCreateBtn = document.getElementById("cancel-create-btn");
    const createModal = document.getElementById("create-modal");
    const createForm = document.getElementById("create-cybernet-form");

    // Trace buttons
    const clearTraceBtn = document.getElementById("clear-trace-btn");

    let activeIdentity = "";

    // Load initial data
    loadCybernets();
    loadStateMachines();
    drawGraph(null);

    // Helper: Add styled lines to the console
    function logToConsole(type, text) {
        const line = document.createElement("div");
        line.classList.add("terminal-line");
        
        if (type === "system") line.classList.add("system-line");
        else if (type === "action") line.classList.add("action-line");
        else if (type === "event") line.classList.add("event-line");
        else if (type === "error") line.classList.add("error-line");
        else if (type === "success") line.classList.add("success-line");
        
        // Add timestamp
        const time = new Date().toLocaleTimeString();
        line.innerText = `[${time}] ${text}`;
        
        terminalOutput.appendChild(line);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }

    // API: Load list of Cybernets
    async function loadCybernets() {
        try {
            const res = await fetch("/api/list");
            const data = await res.json();
            
            // Keep active selection if it still exists
            const currentSelection = selectCybernet.value;
            selectCybernet.innerHTML = '<option value="">-- No Active Identity --</option>';
            
            data.cybernets.forEach(name => {
                const opt = document.createElement("option");
                opt.value = name;
                opt.innerText = name;
                selectCybernet.appendChild(opt);
            });
            
            if (data.cybernets.includes(currentSelection)) {
                selectCybernet.value = currentSelection;
            } else if (activeIdentity) {
                // Active identity got reaped/deleted
                logToConsole("error", `Cybernet '${activeIdentity}' not found. Deselecting.`);
                deselectIdentity();
            }
        } catch (e) {
            logToConsole("error", `Failed to fetch Cybernet list: ${e}`);
        }
    }

    // API: Load list of State Machines
    async function loadStateMachines() {
        try {
            const res = await fetch("/api/state_machines");
            const data = await res.json();
            
            selectStateMachine.innerHTML = '<option value="">Load different State Machine...</option>';
            data.state_machines.forEach(sm => {
                const opt = document.createElement("option");
                opt.value = sm.id;
                opt.innerText = `${sm.name} (${sm.id})`;
                selectStateMachine.appendChild(opt);
            });
        } catch (e) {
            logToConsole("error", `Failed to fetch State Machines: ${e}`);
        }
    }

    // UI: Deselect active identity
    function deselectIdentity() {
        activeIdentity = "";
        selectCybernet.value = "";
        placeholder.classList.remove("hidden");
        arenaContent.classList.add("hidden");
        activeStats.classList.add("hidden");
        
        // Reset simulation history
        simulationPlaceholder.innerText = "Select a Cybernet core to view simulation logs";
        simulationPlaceholder.classList.remove("hidden");
        simulationTableWrapper.classList.add("hidden");
        simulationHistoryList.innerHTML = "";

        // Render generic database graph when no identity is selected
        drawGraph(null);
    }

    // API: Fetch and display identity status sheet
    async function updateIdentitySheet(name) {
        if (!name) {
            deselectIdentity();
            return;
        }

        try {
            const res = await fetch(`/api/status/${name}`);
            if (res.status === 404) {
                logToConsole("error", `Cybernet '${name}' not found.`);
                loadCybernets();
                deselectIdentity();
                return;
            }
            
            const data = await res.json();
            activeIdentity = name;

            // Render Metrics (LLM stats replaced with dashes)
            statModel.innerText = "--";
            statFitness.innerText = "--";
            statTokens.innerText = "--";
            statCost.innerText = "--";

            // Render Arena Content
            if (data.equipped_sm_id) {
                placeholder.classList.add("hidden");
                arenaContent.classList.remove("hidden");
                
                activeSmName.innerText = data.equipped_sm_name || data.equipped_sm_id;
                activeStepId.innerText = data.current_step_id || "sh8_day_start";
                activeStepText.innerText = data.current_step_text || "Awaiting compilation...";
                
                // Show phase badge
                if (data.phase) {
                    phaseBadge.innerText = data.phase.toUpperCase();
                    phaseBadge.className = `active-badge ${data.phase.toLowerCase() === 'night' ? 'accent-badge' : ''}`;
                    phaseBadge.classList.remove("hidden");
                }

                // Render Call Stack frames
                const stack = JSON.parse(data.call_stack || "[]");
                if (stack && stack.length > 0) {
                    callStackContainer.classList.remove("hidden");
                    callStackFrames.innerHTML = "";
                    stack.forEach((frame, idx) => {
                        const frameEl = document.createElement("div");
                        frameEl.className = "stack-frame";
                        frameEl.innerHTML = `
                            <span class="frame-idx">L${idx+1}</span>
                            <span class="frame-sm">${frame.sm_id}</span>
                            <span class="frame-arrow">→</span>
                            <span class="frame-step">${frame.step_id}</span>
                        `;
                        callStackFrames.appendChild(frameEl);
                    });
                } else {
                    callStackContainer.classList.add("hidden");
                }
            } else {
                // Has identity but no state machine equipped yet
                placeholder.classList.add("hidden");
                arenaContent.classList.remove("hidden");
                
                activeSmName.innerText = "No State Machine Equipped";
                activeStepId.innerText = "LOCKED";
                activeStepText.innerText = "Please select a State Machine loadout in the dropdown menu to equip and initialize.";
                phaseBadge.classList.add("hidden");
                callStackContainer.classList.add("hidden");
            }

            activeStats.classList.remove("hidden");
            
            // Render Simulation History
            await updateSimulationHistory(name);

            // Draw active state machine graph
            await drawGraph(name);

        } catch (e) {
            logToConsole("error", `Failed to fetch status for '${name}': ${e}`);
        }
    }

    // API: Fetch and display simulation runs for an identity
    async function updateSimulationHistory(name) {
        if (!name) {
            simulationPlaceholder.classList.remove("hidden");
            simulationTableWrapper.classList.add("hidden");
            simulationHistoryList.innerHTML = "";
            return;
        }

        try {
            const res = await fetch(`/api/simulations/${name}`);
            const data = await res.json();
            const sims = data.simulations || [];

            if (sims.length === 0) {
                simulationPlaceholder.innerText = "No simulation logs found for this identity core.";
                simulationPlaceholder.classList.remove("hidden");
                simulationTableWrapper.classList.add("hidden");
                simulationHistoryList.innerHTML = "";
            } else {
                simulationPlaceholder.classList.add("hidden");
                simulationTableWrapper.classList.remove("hidden");
                simulationHistoryList.innerHTML = "";

                sims.forEach(sim => {
                    const row = document.createElement("tr");
                    
                    // Format accuracy
                    const accVal = parseFloat(sim.accuracy);
                    let accClass = "accuracy-mid";
                    if (accVal >= 0.8) {
                        accClass = "accuracy-high";
                    } else if (accVal < 0.4) {
                        accClass = "accuracy-low";
                    }

                    // Format date
                    let dateStr = sim.created_at;
                    if (dateStr) {
                        try {
                            const d = new Date(dateStr);
                            dateStr = d.toLocaleString();
                        } catch (e) {
                            // Keep raw
                        }
                    } else {
                        dateStr = "N/A";
                    }

                    row.innerHTML = `
                        <td class="run-id-cell">${sim.run_id}</td>
                        <td><span class="accuracy-badge ${accClass}">${accVal.toFixed(4)}</span></td>
                        <td class="date-cell">${dateStr}</td>
                    `;
                    simulationHistoryList.appendChild(row);
                });
            }
        } catch (e) {
            logToConsole("error", `Failed to fetch simulation history: ${e}`);
        }
    }

    // Action: Select Cybernet Core
    selectCybernet.addEventListener("change", (e) => {
        const name = e.target.value;
        if (name) {
            logToConsole("system", `Swapping core loadout to Cybernet Identity: '${name}'`);
            updateIdentitySheet(name);
        } else {
            deselectIdentity();
        }
    });

    // Action: Equip State Machine
    selectStateMachine.addEventListener("change", async (e) => {
        const smId = e.target.value;
        if (!activeIdentity || !smId) return;

        logToConsole("system", `Compiling and equipping State Machine '${smId}' onto '${activeIdentity}'...`);
        try {
            const res = await fetch("/api/equip", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ character_name: activeIdentity, state_machine_id: smId })
            });
            const data = await res.json();
            if (data.success) {
                logToConsole("success", data.message);
                updateIdentitySheet(activeIdentity);
            } else {
                logToConsole("error", data.detail || "Equip compilation error.");
            }
        } catch (e) {
            logToConsole("error", `Equip request failed: ${e}`);
        }
        selectStateMachine.value = ""; // Reset dropdown
    });

    // Action: Tick Compiler Turn
    tickBtn.addEventListener("click", async () => {
        if (!activeIdentity) return;

        tickBtn.classList.add("loading");
        tickBtn.disabled = true;
        logToConsole("system", `Ticking turn step for '${activeIdentity}'...`);

        try {
            const res = await fetch("/api/tick", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ character_name: activeIdentity })
            });
            const data = await res.json();
            
            if (res.status === 400 || res.status === 500) {
                logToConsole("error", data.detail || "Turn execution failed.");
            } else {
                logToConsole("action", `Action Query: ${data.action_taken}`);
                logToConsole("event", `Event logs: ${data.event_message}`);
                
                // Check if reaped
                if (data.event_message.includes("Reaped from DB")) {
                    logToConsole("error", `Evolution check: Cybernet was pruned from the database.`);
                    deselectIdentity();
                    loadCybernets();
                } else {
                    // Refresh sheets
                    await updateIdentitySheet(activeIdentity);
                    // Refresh list (in case clone reproduction spawned a V2 clone!)
                    if (data.event_message.includes("REPRODUCED")) {
                        logToConsole("success", `Reproduction triggered! Mutated child identity spawned in Cyberneticity.`);
                        loadCybernets();
                    }
                }
            }
        } catch (e) {
            logToConsole("error", `Tick request failed: ${e}`);
        } finally {
            tickBtn.classList.remove("loading");
            tickBtn.disabled = false;
        }
    });

    // Action: Spawn Cybernet Form Submit
    createForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const name = document.getElementById("input-name").value.trim();
        const desc = document.getElementById("input-desc").value.trim();

        logToConsole("system", `Compiling and spawning Cybernet Core '${name}'...`);
        try {
            const res = await fetch("/api/create", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: name,
                    description: desc
                })
            });
            const data = await res.json();
            if (res.status === 200 && data.success) {
                logToConsole("success", data.message);
                createModal.classList.add("hidden");
                createForm.reset();
                
                // Reload names and select this new core
                await loadCybernets();
                selectCybernet.value = name;
                updateIdentitySheet(name);
            } else {
                logToConsole("error", data.detail || "Failed to create identity.");
            }
        } catch (err) {
            logToConsole("error", `Create request failed: ${err}`);
        }
    });

    // Modal Drawer triggers
    openCreateBtn.addEventListener("click", () => {
        createModal.classList.remove("hidden");
    });
    
    closeCreateBtn.addEventListener("click", () => {
        createModal.classList.add("hidden");
    });
    
    cancelCreateBtn.addEventListener("click", () => {
        createModal.classList.add("hidden");
    });

    // Click outside drawer closes it
    createModal.addEventListener("click", (e) => {
        if (e.target === createModal) {
            createModal.classList.add("hidden");
        }
    });

    // Clear trace logs
    clearTraceBtn.addEventListener("click", () => {
        terminalOutput.innerHTML = '<div class="terminal-line system-line">[SYSTEM] Terminal logs cleared.</div>';
    });

    // D3 Graph Visualizer logic

    function initGraphVisualizer() {
        const container = document.getElementById("graph-visualizer");
        if (!container) return;
        
        container.innerHTML = "";
        
        canvas = document.createElement("canvas");
        canvas.style.width = "100%";
        canvas.style.height = "100%";
        container.appendChild(canvas);
        
        ctx = canvas.getContext("2d");
        
        // Handle High-DPI displays
        const dpr = window.devicePixelRatio || 1;
        const rect = container.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = height * dpr;
        ctx.scale(dpr, dpr);
        
        const drawWidth = rect.width;
        
        simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(85))
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(drawWidth / 2, height / 2))
            .force("collision", d3.forceCollide().radius(25));
            
        window.simulation = simulation;
            
        // Bind D3 drag behavior to canvas
        d3.select(canvas)
            .call(d3.drag()
                .container(canvas)
                .subject(dragsubject)
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
                
        // Bind mouse movements for hover detection
        canvas.addEventListener("mousemove", (e) => {
            const r = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            // Scale mouse coordinates to match canvas coordinate system dynamically
            mouseX = (e.clientX - r.left) * ((canvas.width / dpr) / r.width);
            mouseY = (e.clientY - r.top) * ((canvas.height / dpr) / r.height);
            
            // Hover detection
            hoveredNode = null;
            for (let i = nodes.length - 1; i >= 0; i--) {
                const node = nodes[i];
                if (Math.hypot(node.x - mouseX, node.y - mouseY) < node.r + 8) {
                    hoveredNode = node;
                    break;
                }
            }
            window.debugMouse = {
                mouseX: mouseX,
                mouseY: mouseY,
                hoveredNode: hoveredNode ? { name: hoveredNode.name, x: hoveredNode.x, y: hoveredNode.y, r: hoveredNode.r } : null
            };
        });
        
        canvas.addEventListener("mouseleave", () => {
            hoveredNode = null;
        });

        // Start 60fps render loop
        requestAnimationFrame(renderLoop);
    }

    function dragsubject(event) {
        const r = canvas.getBoundingClientRect();
        const rect = document.getElementById("graph-visualizer").getBoundingClientRect();
        const x = event.x * (rect.width / r.width);
        const y = event.y * (height / r.height);
        
        for (let i = nodes.length - 1; i >= 0; i--) {
            const node = nodes[i];
            if (Math.hypot(node.x - x, node.y - y) < node.r + 8) {
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
        event.subject.fx = null;
        event.subject.fy = null;
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
        ctx.strokeStyle = "rgba(180, 210, 230, 0.04)";
        for (let x = 0; x < W; x += gs * 4) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
        }
        for (let y = 0; y < H; y += gs * 4) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
        }
    }

    function getRGBColor(node) {
        if (node.active_tag === "shifter") return [46, 213, 115]; // neon green
        if (node.active_tag === "step") return [0, 210, 255]; // neon cyan
        if (node.active_tag === "state_machine") return [160, 100, 255]; // neon purple
        
        if (node.label === "MetaShifter") return [46, 213, 115]; // neon green
        if (node.label === "StateMachine") return [160, 100, 255]; // neon purple
        if (node.label === "TraversalStep") return [0, 210, 255]; // neon cyan
        if (node.label === "IdentityState") return [80, 120, 220]; // slate blue
        if (node.label === "SimulationRun") return [255, 80, 140]; // neon pink
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
        
        const br2 = r * 2.5 + glow * 6;
        const ba2 = 0.08 + glow * 0.025 + act * 0.03;
        const g2 = ctx.createRadialGradient(x, y, 0, x, y, br2);
        g2.addColorStop(0, `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${ba2})`);
        g2.addColorStop(0.5, `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${ba2 * 0.25})`);
        g2.addColorStop(1, `rgba(${c[0]}, ${c[1]}, ${c[2]}, 0)`);
        ctx.fillStyle = g2;
        ctx.beginPath(); ctx.arc(x, y, br2, 0, Math.PI * 2); ctx.fill();
    }

    function drawOrb(ctx, x, y, r, c, act, glow, t, seed, isHov, isSel, refMx, refMy, label) {
        const pulse = 0.85 + 0.15 * Math.sin(t * 2.5 + seed);
        const radius = r * pulse;
        
        // Draw orbital halos for shifters or state machines
        if (label === "MetaShifter") {
            ctx.strokeStyle = `rgba(${c[0]}, ${c[1]}, ${c[2]}, 0.45)`;
            ctx.lineWidth = 0.7;
            ctx.beginPath(); ctx.arc(x, y, radius + 4, 0, Math.PI * 2); ctx.stroke();
            
            ctx.strokeStyle = "rgba(255, 220, 140, 0.3)";
            ctx.setLineDash([3, 3]);
            ctx.beginPath(); ctx.arc(x, y, radius + 7, 0, Math.PI * 2); ctx.stroke();
            ctx.setLineDash([]);
        } else if (label === "StateMachine") {
            ctx.strokeStyle = `rgba(${c[0]}, ${c[1]}, ${c[2]}, 0.4)`;
            ctx.lineWidth = 0.5;
            for (let i = 0; i < 6; i++) {
                const ang = Math.PI / 3 * i + t * 0.5;
                ctx.beginPath();
                ctx.moveTo(x + Math.cos(ang) * (radius + 2), y + Math.sin(ang) * (radius + 2));
                ctx.lineTo(x + Math.cos(ang) * (radius + 4), y + Math.sin(ang) * (radius + 4));
                ctx.stroke();
            }
        }
        
        // Orb shading using radial gradient
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
        
        // Specular highlight highlight
        const sx = x + hxoff * 0.7, sy = y + hyoff * 0.7;
        const sg = ctx.createRadialGradient(sx, sy, 0, sx, sy, radius * 0.4);
        sg.addColorStop(0, `rgba(255, 255, 255, ${0.55 + act * 0.2})`);
        sg.addColorStop(0.4, `rgba(255, 255, 255, 0.15)`);
        sg.addColorStop(1, `rgba(255, 255, 255, 0)`);
        ctx.fillStyle = sg;
        ctx.beginPath(); ctx.arc(sx, sy, radius * 0.4, 0, Math.PI * 2); ctx.fill();
        
        // Inner glowing core
        ctx.fillStyle = `rgba(255, 255, 255, ${0.7 * pulse})`;
        ctx.beginPath(); ctx.arc(x, y, radius * 0.12, 0, Math.PI * 2); ctx.fill();
    }

    function renderLoop(timestamp) {
        if (!ctx) return;
        
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        
        // Dynamically handle resize if container dimensions changed
        if (canvas.width !== rect.width * dpr) {
            canvas.width = rect.width * dpr;
            canvas.height = height * dpr;
            ctx.scale(dpr, dpr);
            simulation.force("center", d3.forceCenter(rect.width / 2, height / 2));
        }
        
        const drawWidth = rect.width;
        const time = timestamp / 1000;
        
        // Clear canvas
        ctx.clearRect(0, 0, drawWidth, height);
        
        // Draw grid background
        drawGrid(ctx, drawWidth, height);
        
        // Draw links
        links.forEach(link => {
            const source = link.source;
            const target = link.target;
            if (source.x && source.y && target.x && target.y) {
                const grad = ctx.createLinearGradient(source.x, source.y, target.x, target.y);
                const colorStart = getRGBColorString(source);
                const colorEnd = getRGBColorString(target);
                
                grad.addColorStop(0, `rgba(${colorStart}, 0.18)`);
                grad.addColorStop(1, `rgba(${colorEnd}, 0.18)`);
                
                ctx.strokeStyle = grad;
                ctx.lineWidth = 1.0;
                ctx.beginPath();
                ctx.moveTo(source.x, source.y);
                ctx.lineTo(target.x, target.y);
                ctx.stroke();
                
                // Animated data flow packet
                const p = (time * 0.35 + (parseInt(source.id) * 0.05 || 0)) % 1.0;
                const px = source.x + (target.x - source.x) * p;
                const py = source.y + (target.y - source.y) * p;
                
                ctx.fillStyle = `rgba(${colorEnd}, 0.55)`;
                ctx.beginPath();
                ctx.arc(px, py, 1.2, 0, Math.PI * 2);
                ctx.fill();
            }
        });
        
        // Draw blooms
        nodes.forEach(node => {
            if (node.x && node.y) {
                const c = getRGBColor(node);
                const glow = node.active_tag ? 2.2 : 0.4;
                const act = node.active_tag === "step" ? 1.6 : 0.1;
                drawBloom(ctx, node.x, node.y, node.r, c, glow, act);
            }
        });
        
        // Draw light orbs
        nodes.forEach(node => {
            if (node.x && node.y) {
                const c = getRGBColor(node);
                const act = node.active_tag === "step" ? 1.6 : 0.1;
                const glow = node.active_tag ? 2.2 : 0.4;
                const isHov = (node === hoveredNode);
                
                drawOrb(ctx, node.x, node.y, node.r, c, act, glow, time, node.seed || 0, isHov, false, mouseX, mouseY, node.label);
            }
        });
        
        // Draw overlays (labels, crosshairs, tooltips)
        nodes.forEach(node => {
            if (node.x && node.y) {
                const isHov = (node === hoveredNode);
                
                if (isHov) {
                    // Rotating crosshair lock brackets
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
                    
                    // Sci-fi Leader line & HUD text box
                    ctx.strokeStyle = "rgba(255, 180, 80, 0.4)";
                    ctx.lineWidth = 0.8;
                    ctx.beginPath();
                    ctx.moveTo(node.x + node.r + 4, node.y);
                    const lx = node.x + node.r + 22;
                    const ly = node.y - 18;
                    ctx.lineTo(lx, ly);
                    ctx.lineTo(lx + 125, ly);
                    ctx.stroke();
                    
                    // Render HUD Metadata text
                    ctx.fillStyle = "rgba(255, 220, 140, 0.98)";
                    ctx.font = "bold 8px 'JetBrains Mono', monospace";
                    ctx.textAlign = "left";
                    ctx.fillText(`${node.label.toUpperCase()}`, lx + 4, ly - 14);
                    
                    ctx.fillStyle = "rgba(180, 210, 230, 0.85)";
                    ctx.font = "8px 'Outfit', sans-serif";
                    ctx.fillText(node.name.length > 21 ? node.name.substring(0, 18) + "..." : node.name, lx + 4, ly - 4);
                } else if (node.active_tag === "step" || node.label === "MetaShifter") {
                    // Constant label on primary nodes
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
        if (!canvas) initGraphVisualizer();
        if (!canvas) return; // Escape if DOM not loaded yet
        
        try {
            const url = name ? `/api/graph?name=${name}` : "/api/graph";
            const res = await fetch(url);
            const graph = await res.json();
            
            const rawNodes = graph.nodes;
            const rawLinks = graph.links;

            // Map nodes to visual orb sizes and assign seeds for animations
            rawNodes.forEach(node => {
                node.seed = Math.random() * 1000;
                if (node.label === "MetaShifter") node.r = 13;
                else if (node.label === "StateMachine") node.r = 10;
                else if (node.label === "TraversalStep") node.r = 8;
                else if (node.label === "IdentityState") node.r = 7;
                else if (node.label === "SimulationRun") node.r = 6;
                else node.r = 5;
            });

            // Preserve positions of existing nodes in the simulation
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
                }
                return node;
            });

            // Map link source/target IDs to actual node references
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
            simulation.alpha(0.3).restart();
            
            window.graphNodes = nodes;
            window.graphLinks = links;

        } catch (e) {
            console.error("D3 Draw Error:", e);
        }
    }

    // Real-time dashboard auto-refresh polling loop
    async function tickDashboard() {
        if (activeIdentity) {
            await updateIdentitySheet(activeIdentity);
        } else {
            await drawGraph(null);
        }
    }

    // Run polling every 1000ms
    const pollInterval = setInterval(tickDashboard, 1000);

    // Cleanup interval on window unload
    window.addEventListener("beforeunload", () => {
        clearInterval(pollInterval);
    });
});
