"use strict";


/* ============================================================
   ATLAS AI STUDIO V2
   ============================================================ */

const AtlasStudio = (() => {

    /* ========================================================
       CONFIGURACIÃ“N
       ======================================================== */

    const CONFIG = {
        statusEndpoint: "/studio/data",
        workflowEndpoint: "/workflows/execute",
        websocketPath: "/ws/workflows",
        reconnectDelay: 3000,
        refreshInterval: 5000,
    };


    /* ========================================================
       ESTADO
       ======================================================== */

    const state = {
        connected: false,
        websocket: null,
        reconnectTimer: null,
        refreshTimer: null,

        selectedAgent: null,
        activeView: "dashboard",

        agents: {},
        receivedEvents: 0,

        workflowRunning: false,
        currentWorkflow: null,
        currentExecutionId: null,
        finalOutput: null,
        stepOutputs: {},

        executionStartedAt: null,
        executionTimer: null,

        workflowZoom: 1,

        metrics: {
            organizations: 0,
            departments: 0,
            agents: 0,
            workflows: 0,
            running: 0,
            errors: 0,
        },
    };


    /* ========================================================
       HELPERS DOM
       ======================================================== */

    function $(
        selector
    ) {
        return document.querySelector(
            selector
        );
    }


    function $$(
        selector
    ) {
        return Array.from(
            document.querySelectorAll(
                selector
            )
        );
    }


    function setText(
        selector,
        value
    ) {

        const element = $(
            selector
        );

        if (!element) {
            return;
        }

        element.textContent = (
            value ?? "-"
        );
    }


    function setHTML(
        selector,
        value
    ) {

        const element = $(
            selector
        );

        if (!element) {
            return;
        }

        element.innerHTML = (
            value ?? ""
        );
    }


    function normalizeState(
        value
    ) {

        return String(
            value || ""
        )
            .trim()
            .toUpperCase()
            .replace(
                /[\s-]+/g,
                "_"
            );
    }


    function escapeHtml(
        value
    ) {

        return String(
            value ?? ""
        )
            .replace(
                /&/g,
                "&amp;"
            )
            .replace(
                /</g,
                "&lt;"
            )
            .replace(
                />/g,
                "&gt;"
            )
            .replace(
                /"/g,
                "&quot;"
            )
            .replace(
                /'/g,
                "&#039;"
            );
    }


    function formatTime(
        date = new Date()
    ) {

        return date.toLocaleTimeString(
            "es-AR",
            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
            }
        );
    }


    function formatDuration(
        milliseconds
    ) {

        const totalSeconds = Math.max(
            0,
            Math.floor(
                Number(
                    milliseconds || 0
                ) / 1000
            )
        );

        const minutes = Math.floor(
            totalSeconds / 60
        );

        const seconds = (
            totalSeconds % 60
        );

        return (
            String(minutes)
                .padStart(2, "0")
            + ":"
            + String(seconds)
                .padStart(2, "0")
        );
    }


    /* ========================================================
       FETCH JSON
       ======================================================== */

    async function fetchJson(
        url,
        options = {}
    ) {

        const response = await fetch(
            url,
            options
        );

        let data = null;

        try {

            data = await response.json();

        } catch {

            data = null;
        }

        if (!response.ok) {

            const detail = (
                data?.detail
                || data?.message
                || `HTTP ${response.status}`
            );

            throw new Error(
                typeof detail === "string"
                    ? detail
                    : JSON.stringify(detail)
            );
        }

        return data;
    }


    /* ========================================================
       LIVE CONSOLE
       ======================================================== */

    function appendConsole(
        message,
        level = "info"
    ) {

        const consoleElement = (
            $("#live-console")
            || $("#console-output")
        );

        if (!consoleElement) {
            return;
        }

        const normalizedLevel = (
            String(
                level || "info"
            ).toLowerCase()
        );

        const line = (
            document.createElement(
                "div"
            )
        );

        line.className = (
            "console-line "
            + `console-${normalizedLevel}`
        );

        line.textContent = (
            `[${formatTime()}] ${message}`
        );

        consoleElement.appendChild(
            line
        );

        consoleElement.scrollTop = (
            consoleElement.scrollHeight
        );
    }


    function clearConsole() {

        const consoleElement = (
            $("#live-console")
            || $("#console-output")
        );

        if (consoleElement) {
            consoleElement.innerHTML = "";
        }
    }
        /* ========================================================
       CONEXIÃ“N / ESTADO
       ======================================================== */

    function setConnection(
        connected,
        label = null
    ) {

        state.connected = Boolean(
            connected
        );

        const connectionDot = (
            $("#connection-dot")
        );

        const sidebarDot = (
            $("#sidebar-status-dot")
        );

        [
            connectionDot,
            sidebarDot,
        ].forEach(
            (element) => {

                if (!element) {
                    return;
                }

                element.classList.remove(
                    "status-ready",
                    "status-warning",
                    "status-error"
                );

                element.classList.add(
                    state.connected
                        ? "status-ready"
                        : "status-warning"
                );
            }
        );

        setText(
            "#connection-label",
            label || (
                state.connected
                    ? "Connected"
                    : "Disconnected"
            )
        );
    }


    function setKernelStatus(
        started,
        version = null
    ) {

        setText(
            "#sidebar-kernel-status",
            started
                ? "Kernel READY"
                : "Kernel OFFLINE"
        );

        if (version) {

            setText(
                "#sidebar-version",
                `Atlas ${version}`
            );
        }
    }


    /* ========================================================
       NAVEGACIÃ“N
       ======================================================== */

    function activateView(
        viewName
    ) {

        state.activeView = (
            viewName
            || "dashboard"
        );

        $$(".nav-item")
            .forEach(
                (item) => {

                    item.classList.toggle(
                        "active",
                        item.dataset.section
                        === state.activeView
                    );
                }
            );

        $$(".studio-view")
            .forEach(
                (view) => {

                    view.classList.toggle(
                        "active",
                        view.dataset.view
                        === state.activeView
                    );
                }
            );

        const titles = {
            dashboard: "Studio Dashboard",
            organizations: "Organizations",
            departments: "Departments",
            agents: "Agents",
            workflows: "Workflows",
            memory: "Memory",
            monitoring: "Monitoring",
            settings: "Settings",
        };

        setText(
            "#page-title",
            titles[state.activeView]
            || "Atlas AI Studio"
        );
    }


    /* ========================================================
       AGENTES
       ======================================================== */

    function kernelNameToDisplayName(
        kernelName
    ) {

        const normalized = String(
            kernelName || ""
        )
            .trim()
            .replace(
                /-agent$/i,
                ""
            );

        if (!normalized) {
            return "Unknown Agent";
        }

        return (
            normalized
                .split("-")
                .filter(Boolean)
                .map(
                    (word) =>
                        word
                            .charAt(0)
                            .toUpperCase()
                        + word.slice(1)
                )
                .join(" ")
            + " Agent"
        );
    }


    function getAgentInitial(
        displayName
    ) {

        const firstWord = String(
            displayName || "A"
        )
            .trim()
            .split(/\s+/)[0];

        return (
            firstWord
                .charAt(0)
                .toUpperCase()
            || "A"
        );
    }


    function inferDepartmentFromAgent(
        kernelName
    ) {

        const normalized = String(
            kernelName || ""
        ).toLowerCase();

        if (
            normalized.includes(
                "planner"
            )
        ) {
            return "planning";
        }

        if (
            normalized.includes(
                "research"
            )
        ) {
            return "research";
        }

        if (
            normalized.includes(
                "engineering"
            )
        ) {
            return "engineering";
        }

        if (
            normalized.includes(
                "security"
            )
        ) {
            return "security";
        }

        if (
            normalized.includes(
                "general"
            )
        ) {
            return "operations";
        }

        return "unassigned";
    }


    function getAgentDescription(
        kernelName
    ) {

        const normalized = String(
            kernelName || ""
        ).toLowerCase();

        if (
            normalized.includes(
                "planner"
            )
        ) {
            return (
                "Planning and workflow coordination"
            );
        }

        if (
            normalized.includes(
                "research"
            )
        ) {
            return (
                "Research and information analysis"
            );
        }

        if (
            normalized.includes(
                "engineering"
            )
        ) {
            return (
                "Engineering and implementation"
            );
        }

        if (
            normalized.includes(
                "security"
            )
        ) {
            return (
                "Security analysis and risk control"
            );
        }

        if (
            normalized.includes(
                "general"
            )
        ) {
            return (
                "General reasoning and operations"
            );
        }

        return "Kernel managed agent";
    }


    function synchronizeKernelAgents(
        data
    ) {

        const previousAgents = (
            state.agents || {}
        );

        const nextAgents = {};

        nextAgents[
            "Executive Agent"
        ] = {
            role: (
                "Enterprise orchestration controller"
            ),

            department: (
                data?.executive
                    ?.default_department
                || "planning"
            ),

            model: (
                "Kernel executive runtime"
            ),

            capabilities: (
                "Orchestration, delegation and decisions"
            ),

            state: normalizeState(
                data?.executive?.status
                || previousAgents[
                    "Executive Agent"
                ]?.state
                || "READY"
            ),

            duration: (
                previousAgents[
                    "Executive Agent"
                ]?.duration
                || "0.00 s"
            ),

            events: (
                previousAgents[
                    "Executive Agent"
                ]?.events
                || 0
            ),

            initial: "E",

            kernelName: "executive",

            isController: true,
        };


        const registeredNames = (
            data?.agents?.names
            || []
        );


        registeredNames.forEach(
            (kernelName) => {

                const displayName = (
                    kernelNameToDisplayName(
                        kernelName
                    )
                );

                const previous = (
                    previousAgents[
                        displayName
                    ]
                    || {}
                );

                nextAgents[
                    displayName
                ] = {
                    role: (
                        getAgentDescription(
                            kernelName
                        )
                    ),

                    department: (
                        inferDepartmentFromAgent(
                            kernelName
                        )
                    ),

                    model: (
                        data?.llm?.default
                            ? `LLM: ${data.llm.default}`
                            : "Kernel managed"
                    ),

                    capabilities: (
                        "Registered in Atlas Kernel"
                    ),

                    state: (
                        previous.state
                        || "AVAILABLE"
                    ),

                    duration: (
                        previous.duration
                        || "0.00 s"
                    ),

                    events: (
                        previous.events
                        || 0
                    ),

                    initial: (
                        getAgentInitial(
                            displayName
                        )
                    ),

                    kernelName: kernelName,

                    isKernelAgent: true,
                };
            }
        );


        nextAgents[
            "Final Output"
        ] = {
            role: (
                "Workflow final response"
            ),

            department: "executive",

            model: "System output",

            capabilities: (
                "Aggregation and delivery"
            ),

            state: (
                previousAgents[
                    "Final Output"
                ]?.state
                || "WAITING"
            ),

            duration: (
                previousAgents[
                    "Final Output"
                ]?.duration
                || "0.00 s"
            ),

            events: (
                previousAgents[
                    "Final Output"
                ]?.events
                || 0
            ),

            initial: "âœ“",

            kernelName: "final-output",

            isOutput: true,
        };


        state.agents = (
            nextAgents
        );


        if (
            !state.selectedAgent
            || !state.agents[
                state.selectedAgent
            ]
        ) {
            state.selectedAgent = (
                "Executive Agent"
            );
        }
    }


    function getKernelAgentNames() {

        return Object.keys(
            state.agents
        ).filter(
            (name) =>
                state.agents[
                    name
                ]?.isKernelAgent
        );
    }


    /* ========================================================
       CANVAS / LAYOUT
       ======================================================== */

    function getCanvasLayout() {

        const kernelAgents = (
            getKernelAgentNames()
        );

        const preferredOrder = [
            "Planner Agent",
            "Research Agent",
            "Engineering Agent",
            "General Agent",
            "Security Agent",
        ];

        const ordered = [
            ...preferredOrder.filter(
                (name) =>
                    kernelAgents.includes(
                        name
                    )
            ),

            ...kernelAgents.filter(
                (name) =>
                    !preferredOrder.includes(
                        name
                    )
            ),
        ];


        const layouts = {
            1: [
                [50, 48],
            ],

            2: [
                [32, 48],
                [68, 48],
            ],

            3: [
                [50, 36],
                [30, 62],
                [70, 62],
            ],

            4: [
                [30, 38],
                [70, 38],
                [30, 68],
                [70, 68],
            ],

            5: [
                [50, 32],
                [25, 52],
                [75, 52],
                [32, 74],
                [68, 74],
            ],
        };


        const points = (
            layouts[
                Math.min(
                    ordered.length,
                    5
                )
            ]
            || []
        );


        return ordered.map(
            (
                name,
                index
            ) => {

                if (
                    index
                    < points.length
                ) {
                    return {
                        name,
                        x: points[index][0],
                        y: points[index][1],
                    };
                }

                const extraIndex = (
                    index
                    - points.length
                );

                return {
                    name,

                    x: (
                        18
                        + (
                            extraIndex % 5
                        ) * 16
                    ),

                    y: (
                        82
                        + Math.floor(
                            extraIndex / 5
                        ) * 10
                    ),
                };
            }
        );
    }


    function pointToSvg(
        xPercent,
        yPercent
    ) {

        return {
            x: (
                xPercent * 10
            ),

            y: (
                yPercent * 5.2
            ),
        };
    }


    function createSvgEdge(
        x1,
        y1,
        x2,
        y2
    ) {

        const start = (
            pointToSvg(
                x1,
                y1
            )
        );

        const end = (
            pointToSvg(
                x2,
                y2
            )
        );

        const middleY = (
            (
                start.y
                + end.y
            )
            / 2
        );


        const path = (
            document.createElementNS(
                "http://www.w3.org/2000/svg",
                "path"
            )
        );


        path.setAttribute(
            "d",
            (
                `M${start.x} ${start.y} `
                + `C${start.x} ${middleY}, `
                + `${end.x} ${middleY}, `
                + `${end.x} ${end.y}`
            )
        );


        path.setAttribute(
            "class",
            "workflow-edge"
        );


        return path;
    }
        /* ========================================================
       CREAR NODO DE WORKFLOW
       ======================================================== */

    function createWorkflowNode(
        name,
        x,
        y
    ) {

        const agent = (
            state.agents[name]
            || {}
        );

        const node = (
            document.createElement(
                "button"
            )
        );

        node.type = "button";

        node.className = (
            "workflow-node"
        );

        node.dataset.agent = (
            name
        );

        node.style.left = (
            `${x}%`
        );

        node.style.top = (
            `${y}%`
        );

        const normalizedState = (
            normalizeState(
                agent.state
                || "AVAILABLE"
            )
        );

        node.dataset.state = (
            normalizedState
        );

        node.innerHTML = `
            <span class="node-avatar">
                ${escapeHtml(
                    agent.initial
                    || getAgentInitial(name)
                )}
            </span>

            <span class="node-content">

                <strong>
                    ${escapeHtml(name)}
                </strong>

                <small>
                    ${escapeHtml(
                        agent.role
                        || agent.department
                        || "Atlas Agent"
                    )}
                </small>

            </span>

            <span class="node-status">
                ${escapeHtml(
                    normalizedState
                )}
            </span>
        `;

        return node;
    }


    /* ========================================================
       RENDER DEL CANVAS
       ======================================================== */

    function renderWorkflowCanvas() {

        const canvas = (
            $("#workflow-canvas")
        );

        if (!canvas) {
            return;
        }


        canvas.innerHTML = "";


        const svg = (
            document.createElementNS(
                "http://www.w3.org/2000/svg",
                "svg"
            )
        );

        svg.setAttribute(
            "class",
            "workflow-connections"
        );

        svg.setAttribute(
            "viewBox",
            "0 0 1000 520"
        );

        svg.setAttribute(
            "preserveAspectRatio",
            "none"
        );


        canvas.appendChild(
            svg
        );


        const executivePoint = {
            name: "Executive Agent",
            x: 50,
            y: 10,
        };


        const outputPoint = {
            name: "Final Output",
            x: 50,
            y: 94,
        };


        const agentLayout = (
            getCanvasLayout()
        );


        agentLayout.forEach(
            (point) => {

                svg.appendChild(
                    createSvgEdge(
                        executivePoint.x,
                        executivePoint.y,
                        point.x,
                        point.y
                    )
                );


                svg.appendChild(
                    createSvgEdge(
                        point.x,
                        point.y,
                        outputPoint.x,
                        outputPoint.y
                    )
                );
            }
        );


        canvas.appendChild(
            createWorkflowNode(
                executivePoint.name,
                executivePoint.x,
                executivePoint.y
            )
        );


        agentLayout.forEach(
            (point) => {

                canvas.appendChild(
                    createWorkflowNode(
                        point.name,
                        point.x,
                        point.y
                    )
                );
            }
        );


        canvas.appendChild(
            createWorkflowNode(
                outputPoint.name,
                outputPoint.x,
                outputPoint.y
            )
        );


        setWorkflowZoom(
            state.workflowZoom
        );
    }


    /* ========================================================
       ZOOM DEL CANVAS
       ======================================================== */

    function setWorkflowZoom(
        zoom
    ) {

        const normalized = Math.min(
            1.5,
            Math.max(
                0.6,
                Number(
                    zoom || 1
                )
            )
        );

        state.workflowZoom = (
            normalized
        );


        const canvas = (
            $("#workflow-canvas")
        );

        if (canvas) {

            canvas.style.transform = (
                `scale(${normalized})`
            );

            canvas.style.transformOrigin = (
                "center center"
            );
        }


        setText(
            "#zoom-value",
            `${Math.round(
                normalized * 100
            )}%`
        );
    }


    /* ========================================================
       ACTUALIZAR NODO
       ======================================================== */

    function updateNode(
        agentName,
        status
    ) {

        if (
            !agentName
            || !state.agents[
                agentName
            ]
        ) {
            return;
        }


        const normalized = (
            normalizeState(
                status
            )
        );


        state.agents[
            agentName
        ].state = (
            normalized
        );


        const node = (
            $$(".workflow-node")
                .find(
                    (element) =>
                        element.dataset.agent
                        === agentName
                )
        );


        if (!node) {
            return;
        }


        node.dataset.state = (
            normalized
        );


        const statusElement = (
            node.querySelector(
                ".node-status"
            )
        );


        if (statusElement) {

            statusElement.textContent = (
                normalized
            );
        }
    }


    /* ========================================================
       RESET VISUAL DE EJECUCIÃ“N
       ======================================================== */

    function resetExecutionVisuals() {

        Object.keys(
            state.agents
        ).forEach(
            (name) => {

                if (
                    name
                    === "Final Output"
                ) {

                    state.agents[
                        name
                    ].state = "WAITING";

                } else {

                    state.agents[
                        name
                    ].state = (
                        name
                        === "Executive Agent"
                            ? "READY"
                            : "AVAILABLE"
                    );
                }


                state.agents[
                    name
                ].duration = (
                    "0.00 s"
                );

                state.agents[
                    name
                ].events = 0;
            }
        );


        renderWorkflowCanvas();

        clearTimeline();

        setText(
            "#metric-running",
            "0"
        );

        setText(
            "#metric-errors",
            "0"
        );
    }


    /* ========================================================
       SELECCIÃ“N DE AGENTE
       ======================================================== */

    function selectAgent(
        agentName
    ) {

        if (
            !agentName
            || !state.agents[
                agentName
            ]
        ) {
            return;
        }


        state.selectedAgent = (
            agentName
        );


        $$(".workflow-node")
            .forEach(
                (node) => {

                    node.classList.toggle(
                        "selected",
                        node.dataset.agent
                        === agentName
                    );
                }
            );


        renderAgentInspector(
            agentName
        );
    }


    /* ========================================================
       INSPECTOR DE AGENTE
       ======================================================== */

    function renderMarkdownOutput(
        value
    ) {

        const source = stringifyOutput(value);

        if (source === "No output available.") {
            return '<div class="output-empty">No output available.</div>';
        }

        const escaped = escapeHtml(source);
        const lines = escaped.split(/\r?\n/);
        const html = [];

        let inOrderedList = false;
        let inUnorderedList = false;

        const closeLists = () => {
            if (inOrderedList) {
                html.push("</ol>");
                inOrderedList = false;
            }

            if (inUnorderedList) {
                html.push("</ul>");
                inUnorderedList = false;
            }
        };

        const formatInline = (line) => (
            line
                .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
                .replace(/`([^`]+)`/g, "<code>$1</code>")
        );

        lines.forEach((rawLine) => {
            const line = rawLine.trimEnd();

            if (!line.trim()) {
                closeLists();
                html.push('<div class="output-spacer"></div>');
                return;
            }

            const heading = line.match(/^(#{1,6})\s+(.*)$/);

            if (heading) {
                closeLists();

                const level = Math.min(heading[1].length, 4);

                html.push(
                    `<h${level} class="output-heading output-heading-${level}">`
                    + formatInline(heading[2])
                    + `</h${level}>`
                );

                return;
            }

            const ordered = line.match(/^\s*\d+\.\s+(.*)$/);

            if (ordered) {
                if (inUnorderedList) {
                    html.push("</ul>");
                    inUnorderedList = false;
                }

                if (!inOrderedList) {
                    html.push('<ol class="output-list output-list-ordered">');
                    inOrderedList = true;
                }

                html.push("<li>" + formatInline(ordered[1]) + "</li>");
                return;
            }

            const unordered = line.match(/^\s*[-*]\s+(.*)$/);

            if (unordered) {
                if (inOrderedList) {
                    html.push("</ol>");
                    inOrderedList = false;
                }

                if (!inUnorderedList) {
                    html.push('<ul class="output-list output-list-unordered">');
                    inUnorderedList = true;
                }

                html.push("<li>" + formatInline(unordered[1]) + "</li>");
                return;
            }

            closeLists();

            html.push(
                '<p class="output-paragraph">'
                + formatInline(line)
                + "</p>"
            );
        });

        closeLists();

        return html.join("");
    }


    function stringifyOutput(
        value
    ) {

        if (
            value === null
            || value === undefined
            || value === ""
        ) {
            return "No output available.";
        }

        if (
            typeof value === "string"
        ) {
            return value;
        }

        try {
            return JSON.stringify(
                value,
                null,
                2
            );
        } catch {
            return String(value);
        }
    }


    function normalizeStepOutputs(
        rawSteps
    ) {

        if (!rawSteps) {
            return {};
        }

        if (
            !Array.isArray(rawSteps)
            && typeof rawSteps === "object"
        ) {
            return rawSteps;
        }

        const normalized = {};

        if (!Array.isArray(rawSteps)) {
            return normalized;
        }

        rawSteps.forEach(
            (step) => {

                if (
                    !step
                    || typeof step !== "object"
                ) {
                    return;
                }

                const candidates = [
                    step.step_id,
                    step.id,
                    step.agent_id,
                    step.agent,
                    step.agent_name,
                    step.department_id,
                    step.department,
                    step.name,
                ].filter(Boolean);

                candidates.forEach(
                    (key) => {
                        normalized[
                            String(key)
                        ] = step;
                    }
                );
            }
        );

        return normalized;
    }


    function getAgentOutput(
        agentName
    ) {

        if (
            agentName === "Final Output"
        ) {
            return state.finalOutput;
        }

        const agent = (
            state.agents[
                agentName
            ]
            || {}
        );

        const candidates = [
            agent.kernelName,
            agentName,
            String(agent.kernelName || "")
                .replace(/-agent$/i, ""),
            String(agentName || "")
                .replace(/\s+Agent$/i, "")
                .toLowerCase(),
        ].filter(Boolean);

        for (
            const key
            of candidates
        ) {
            if (
                Object.prototype.hasOwnProperty.call(
                    state.stepOutputs,
                    key
                )
            ) {
                const step = (
                    state.stepOutputs[key]
                );

                return (
                    step?.output
                    ?? step?.result?.output
                    ?? step?.result
                    ?? step?.execution?.output
                    ?? step
                );
            }
        }

        return null;
    }


    function renderAgentInspector(
        agentName
    ) {

        const agent = (
            state.agents[
                agentName
            ]
        );

        if (!agent) {
            return;
        }

        setText(
            "#inspector-title",
            agentName
        );

        setText(
            "#inspector-name",
            agentName
        );

        setText(
            "#inspector-role",
            agent.role
            || "-"
        );

        setText(
            "#inspector-department",
            agent.department
            || "-"
        );

        setText(
            "#inspector-model",
            agent.model
            || "-"
        );

        setText(
            "#inspector-capabilities",
            agent.capabilities
            || "-"
        );

        setText(
            "#inspector-state",
            normalizeState(
                agent.state
                || "-"
            )
        );

        setText(
            "#inspector-duration",
            agent.duration
            || "0.00 s"
        );

        setText(
            "#inspector-events",
            agent.events
            || 0
        );

        setText(
            "#inspector-last-run",
            (
                agent.lastRun
                || (
                    state.currentWorkflow
                        ? state.currentWorkflow
                        : "No executions"
                )
            )
        );


        const outputContainer = (
            $("#inspector-output")
        );

        if (outputContainer) {
            outputContainer.dataset.kind = (
                agentName === "Final Output"
                    ? "final"
                    : "agent"
            );

            outputContainer.dataset.status = (
                normalizeState(
                    agent.state
                    || ""
                ).toLowerCase()
            );
        }

        const avatar = (
            $(".agent-avatar")
        );

        if (avatar) {
            avatar.textContent = (
                agent.initial
                || getAgentInitial(
                    agentName
                )
            );
        }

        const statePill = (
            $("#inspector-state")
        );

        if (statePill) {
            statePill.className = (
                "state-pill state-"
                + String(
                    normalizeState(
                        agent.state
                        || "ready"
                    )
                ).toLowerCase()
            );
        }

        setHTML(
            "#inspector-output",
            renderMarkdownOutput(
                getAgentOutput(
                    agentName
                )
            )
        );
    }


    /* ========================================================
       DETALLES DEL AGENTE
       ======================================================== */

    function openSelectedAgentDetails() {

        activateView(
            "agents"
        );


        appendConsole(
            (
                "Abriendo detalles de "
                + (
                    state.selectedAgent
                    || "agente"
                )
                + "."
            ),
            "info"
        );
    }


    /* ========================================================
       TIMELINE
       ======================================================== */

    function getTimelineContainer() {

        return (
            $("#execution-timeline")
            || $("#timeline-list")
            || $("#timeline")
        );
    }


    function clearTimeline() {

        const timeline = (
            getTimelineContainer()
        );

        if (!timeline) {
            return;
        }


        timeline.innerHTML = "";
    }


    function addTimelineEvent(
        eventType,
        agentName = null,
        status = null,
        message = null
    ) {

        const timeline = (
            getTimelineContainer()
        );

        if (!timeline) {
            return;
        }


        const item = (
            document.createElement(
                "div"
            )
        );


        const normalizedStatus = (
            normalizeState(
                status
                || eventType
            )
        );


        item.className = (
            "timeline-item"
        );

        item.dataset.status = (
            normalizedStatus
        );


        const title = (
            agentName
            || eventType
            || "Workflow event"
        );


        item.innerHTML = `
            <div class="timeline-marker"></div>

            <div class="timeline-content">

                <div class="timeline-header">

                    <strong>
                        ${escapeHtml(title)}
                    </strong>

                    <span>
                        ${escapeHtml(
                            formatTime()
                        )}
                    </span>

                </div>

                <div class="timeline-meta">

                    <span>
                        ${escapeHtml(
                            normalizedStatus
                        )}
                    </span>

                    ${
                        message
                            ? `
                                <span>
                                    ${escapeHtml(
                                        message
                                    )}
                                </span>
                              `
                            : ""
                    }

                </div>

            </div>
        `;


        timeline.appendChild(
            item
        );


        timeline.scrollTop = (
            timeline.scrollHeight
        );
    }


    /* ========================================================
       MÃ‰TRICAS
       ======================================================== */

    function updateMetrics(
        data
    ) {

        const organizationCount = (
            data?.organization
                ?.organization_name
                ? 1
                : 0
        );


        const departmentCount = (
            data
                ?.organization
                ?.organization
                ?.departments
                ?.total_departments
            || 0
        );


        const agentCount = (
            data?.agents?.count
            || 0
        );


        const workflowCount = (
            data
                ?.workflow_registry
                ?.workflow_count
            || 0
        );


        const runningCount = (
            data
                ?.workflow_engine
                ?.active_executions
            || (
                state.workflowRunning
                    ? 1
                    : 0
            )
        );


        const errorCount = (
            data
                ?.workflow_engine
                ?.failed_executions
            || 0
        );


        state.metrics = {
            organizations: organizationCount,
            departments: departmentCount,
            agents: agentCount,
            workflows: workflowCount,
            running: runningCount,
            errors: errorCount,
        };


        setText(
            "#metric-organizations",
            organizationCount
        );


        setText(
            "#metric-departments",
            departmentCount
        );


        setText(
            "#metric-agents",
            agentCount
        );


        setText(
            "#metric-workflows",
            workflowCount
        );


        setText(
            "#metric-running",
            runningCount
        );


        setText(
            "#metric-errors",
            errorCount
        );
    }


    /* ========================================================
       DATOS DEL KERNEL
       ======================================================== */

    function applyStudioData(
        data
    ) {

        if (!data) {
            return;
        }


        setKernelStatus(
            Boolean(
                data?.kernel?.started
            ),
            data?.kernel?.version
        );


        synchronizeKernelAgents(
            data
        );


        updateMetrics(
            data
        );


        renderWorkflowCanvas();


        if (
            state.selectedAgent
            && state.agents[
                state.selectedAgent
            ]
        ) {

            selectAgent(
                state.selectedAgent
            );

        } else {

            selectAgent(
                "Executive Agent"
            );
        }


        const executiveStatus = (
            normalizeState(
                data?.executive?.status
                || "READY"
            )
        );


        updateNode(
            "Executive Agent",
            executiveStatus
        );
    }


    /* ========================================================
       REFRESH DEL STUDIO
       ======================================================== */

    async function refreshStatus(
        options = {}
    ) {

        const silent = Boolean(
            options.silent
        );


        if (!silent) {

            appendConsole(
                (
                    "Sincronizando Atlas Studio "
                    + "con el Kernel..."
                ),
                "info"
            );
        }


        try {

            const data = (
                await fetchJson(
                    CONFIG.statusEndpoint
                )
            );


            if (
                !data
                || !data.success
            ) {

                throw new Error(
                    "Respuesta invÃ¡lida de /studio/data."
                );
            }


            applyStudioData(
                data
            );


            if (!silent) {

                const agentCount = (
                    data?.agents?.count
                    || 0
                );


                const departmentCount = (
                    data
                        ?.organization
                        ?.organization
                        ?.departments
                        ?.total_departments
                    || 0
                );


                const workflowCount = (
                    data
                        ?.workflow_registry
                        ?.workflow_count
                    || 0
                );


                appendConsole(
                    (
                        "Kernel sincronizado: "
                        + `${agentCount} agentes, `
                        + `${departmentCount} departamentos, `
                        + `${workflowCount} workflows.`
                    ),
                    "success"
                );
            }


            return data;

        } catch (error) {

            if (!silent) {

                appendConsole(
                    (
                        "No se pudo sincronizar "
                        + "Atlas Studio: "
                        + error.message
                    ),
                    "error"
                );
            }


            throw error;
        }
    }
        /* ========================================================
       RESOLVER AGENTE DESDE EVENTO
       ======================================================== */

    function resolveAgentName(
        rawValue
    ) {

        if (!rawValue) {
            return null;
        }


        const raw = String(
            rawValue
        )
            .trim()
            .toLowerCase()
            .replace(
                /_/g,
                "-"
            );


        const aliases = {
            executive: "Executive Agent",

            planning: "Planner Agent",
            planner: "Planner Agent",
            "planner-agent": "Planner Agent",

            research: "Research Agent",
            "research-agent": "Research Agent",

            engineering: "Engineering Agent",
            "engineering-agent": "Engineering Agent",

            operations: "General Agent",
            general: "General Agent",
            "general-agent": "General Agent",

            security: "Security Agent",
            "security-agent": "Security Agent",

            output: "Final Output",
            "final-output": "Final Output",
        };


        if (
            aliases[
                raw
            ]
        ) {

            return aliases[
                raw
            ];
        }


        for (
            const [
                displayName,
                agent
            ]
            of Object.entries(
                state.agents
            )
        ) {

            const kernelName = String(
                agent.kernelName
                || ""
            )
                .trim()
                .toLowerCase();


            if (
                kernelName
                && kernelName
                === raw
            ) {

                return displayName;
            }


            const normalizedDisplay = (
                displayName
                    .toLowerCase()
                    .replace(
                        /\s+/g,
                        "-"
                    )
            );


            if (
                normalizedDisplay
                === raw
            ) {

                return displayName;
            }
        }


        return null;
    }


    /* ========================================================
       NORMALIZAR EVENTO WEBSOCKET
       ======================================================== */

    function unwrapWorkflowEvent(
        event
    ) {

        if (
            event?.type
            === "workflow-event"
            && event?.data
        ) {

            return event.data;
        }


        return event || {};
    }


    /* ========================================================
       DETECTAR AGENTE DESDE EVENTO
       ======================================================== */

    function findEventAgent(
        event
    ) {

        const core = (
            unwrapWorkflowEvent(
                event
            )
        );


        const details = (
            core?.data
            || {}
        );


        const candidates = [
            details.agent_id,
            details.agent,
            details.agent_name,

            core.agent_id,
            core.agent,
            core.agent_name,

            details.department_id,
            details.department,

            core.department_id,
            core.department,

            core.step_id,
        ].filter(Boolean);


        for (
            const candidate
            of candidates
        ) {

            const resolved = (
                resolveAgentName(
                    candidate
                )
            );


            if (resolved) {

                return resolved;
            }
        }


        return null;
    }


    /* ========================================================
       DETECTAR STATUS DESDE EVENTO
       ======================================================== */

    function findEventStatus(
        event
    ) {

        const core = (
            unwrapWorkflowEvent(
                event
            )
        );


        const details = (
            core?.data
            || {}
        );


        const explicitStatus = (
            details.status
            || details.state
            || core.status
            || core.state
            || null
        );


        if (
            explicitStatus
        ) {

            return normalizeState(
                explicitStatus
            );
        }


        const eventType = String(
            core.event_type
            || core.type
            || ""
        )
            .trim()
            .toLowerCase();


        switch (
            eventType
        ) {

            case "step-ready":
                return "READY";

            case "step-started":
                return "RUNNING";

            case "step-completed":
                return "COMPLETED";

            case "step-failed":
                return "FAILED";

            case "step-skipped":
                return "SKIPPED";

            case "step-blocked":
                return "BLOCKED";

            case "workflow-started":
                return "RUNNING";

            case "workflow-finished":
                return "COMPLETED";

            case "workflow-failed":
                return "FAILED";

            default:
                return null;
        }
    }


    /* ========================================================
       MENSAJE LEGIBLE DE EVENTO
       ======================================================== */

    function buildEventMessage(
        event
    ) {

        const core = (
            unwrapWorkflowEvent(
                event
            )
        );


        const details = (
            core?.data
            || {}
        );


        const eventType = String(
            core.event_type
            || core.type
            || event?.type
            || "workflow-event"
        );


        const stepName = (
            details.step_name
            || core.step_name
            || core.step_id
            || ""
        );


        const department = (
            details.department_id
            || core.department_id
            || ""
        );


        const agent = (
            findEventAgent(
                event
            )
        );


        const parts = [
            eventType,
        ];


        if (
            stepName
        ) {

            parts.push(
                stepName
            );
        }


        if (
            department
        ) {

            parts.push(
                department
            );
        }


        if (
            agent
        ) {

            parts.push(
                agent
            );
        }


        return parts.join(
            " Â· "
        );
    }


    /* ========================================================
       PROCESAR EVENTO DE WORKFLOW
       ======================================================== */

    function handleWorkflowEvent(
        event
    ) {

        state.receivedEvents += 1;


        const core = (
            unwrapWorkflowEvent(
                event
            )
        );


        const details = (
            core?.data
            || {}
        );


        const eventType = String(
            core.event_type
            || core.type
            || event?.type
            || "workflow-event"
        )
            .trim()
            .toLowerCase();


        const agentName = (
            findEventAgent(
                event
            )
        );


        const status = (
            findEventStatus(
                event
            )
        );


        const message = (
            buildEventMessage(
                event
            )
        );


        let level = "info";


        if (
            status === "FAILED"
            || status === "ERROR"
        ) {

            level = "error";

        } else if (
            status === "COMPLETED"
            || status === "SUCCESS"
        ) {

            level = "success";
        }


        appendConsole(
            message,
            level
        );


        addTimelineEvent(
            eventType,
            agentName,
            status,
            details.message
            || core.message
            || null
        );


        if (
            core.execution_id
        ) {

            state.currentExecutionId = (
                core.execution_id
            );
        }


        if (
            eventType
            === "workflow-started"
        ) {

            state.workflowRunning = true;


            updateNode(
                "Executive Agent",
                "RUNNING"
            );


            selectAgent(
                "Executive Agent"
            );


            setText(
                "#metric-running",
                "1"
            );
        }


        if (
            agentName
            && status
        ) {

            const agent = (
                state.agents[
                    agentName
                ]
            );


            if (
                agent
            ) {

                agent.events = (
                    Number(
                        agent.events
                        || 0
                    )
                    + 1
                );
            }


            updateNode(
                agentName,
                status
            );


            selectAgent(
                agentName
            );
        }


        if (
            eventType
            === "workflow-finished"
        ) {

            state.workflowRunning = false;


            updateNode(
                "Executive Agent",
                "COMPLETED"
            );


            updateNode(
                "Final Output",
                "COMPLETED"
            );


            selectAgent(
                "Final Output"
            );


            setText(
                "#metric-running",
                "0"
            );
        }


        if (
            eventType
            === "workflow-failed"
        ) {

            state.workflowRunning = false;


            updateNode(
                "Executive Agent",
                "FAILED"
            );


            updateNode(
                "Final Output",
                "FAILED"
            );


            setText(
                "#metric-running",
                "0"
            );


            setText(
                "#metric-errors",
                Number(
                    state.metrics.errors
                    || 0
                )
                + 1
            );
        }
    }


    /* ========================================================
       WEBSOCKET
       ======================================================== */

    function getWebSocketUrl() {

        const protocol = (
            window.location.protocol
            === "https:"
                ? "wss:"
                : "ws:"
        );


        return (
            `${protocol}//`
            + window.location.host
            + CONFIG.websocketPath
        );
    }


    function scheduleReconnect() {

        if (
            state.reconnectTimer
        ) {

            return;
        }


        state.reconnectTimer = (
            window.setTimeout(
                () => {

                    state.reconnectTimer = (
                        null
                    );


                    connectWebSocket();

                },
                CONFIG.reconnectDelay
            )
        );
    }


    function connectWebSocket() {

        if (
            state.websocket
            && (
                state.websocket.readyState
                === WebSocket.OPEN

                || state.websocket.readyState
                === WebSocket.CONNECTING
            )
        ) {

            return;
        }


        const url = (
            getWebSocketUrl()
        );


        try {

            state.websocket = (
                new WebSocket(
                    url
                )
            );

        } catch (error) {

            setConnection(
                false,
                "Unavailable"
            );


            appendConsole(
                (
                    "No se pudo abrir "
                    + "WebSocket: "
                    + error.message
                ),
                "warning"
            );


            scheduleReconnect();


            return;
        }


        state.websocket
            .addEventListener(
                "open",
                () => {

                    setConnection(
                        true,
                        "Connected"
                    );


                    appendConsole(
                        (
                            "Canal WebSocket "
                            + "conectado."
                        ),
                        "success"
                    );
                }
            );


        state.websocket
            .addEventListener(
                "message",
                (message) => {

                    try {

                        const event = (
                            JSON.parse(
                                message.data
                            )
                        );


                        handleWorkflowEvent(
                            event
                        );

                    } catch (error) {

                        appendConsole(
                            (
                                "Evento WebSocket "
                                + "no interpretable: "
                                + String(
                                    message.data
                                )
                            ),
                            "warning"
                        );
                    }
                }
            );


        state.websocket
            .addEventListener(
                "close",
                () => {

                    setConnection(
                        false,
                        "Reconnecting"
                    );


                    appendConsole(
                        (
                            "WebSocket desconectado. "
                            + "Reintentando..."
                        ),
                        "warning"
                    );


                    scheduleReconnect();
                }
            );


        state.websocket
            .addEventListener(
                "error",
                () => {

                    setConnection(
                        false,
                        "Connection error"
                    );
                }
            );
    }


    function disconnectWebSocket() {

        if (
            state.reconnectTimer
        ) {

            window.clearTimeout(
                state.reconnectTimer
            );


            state.reconnectTimer = (
                null
            );
        }


        if (
            state.refreshTimer
        ) {

            window.clearInterval(
                state.refreshTimer
            );


            state.refreshTimer = (
                null
            );
        }


        if (
            state.websocket
        ) {

            try {

                state.websocket.close(
                    1000,
                    "Atlas Studio closed"
                );

            } catch {

                /*
                No hace falta propagar
                el error al cerrar.
                */
            }
        }


        state.websocket = null;
    }


    /* ========================================================
       CRONÃ“METRO DE EJECUCIÃ“N
       ======================================================== */

    function startExecutionClock() {

        state.executionStartedAt = (
            performance.now()
        );


        if (
            state.executionTimer
        ) {

            window.clearInterval(
                state.executionTimer
            );
        }


        state.executionTimer = (
            window.setInterval(
                () => {

                    if (
                        state.executionStartedAt
                        === null
                    ) {

                        return;
                    }


                    const elapsed = (
                        performance.now()
                        - state.executionStartedAt
                    );


                    const formatted = (
                        (
                            elapsed
                            / 1000
                        )
                            .toFixed(2)
                        + " s"
                    );


                    setText(
                        "#timeline-duration",
                        formatted
                    );


                    setText(
                        "#execution-duration",
                        formatDuration(
                            elapsed
                        )
                    );

                },
                100
            )
        );
    }


    function stopExecutionClock() {

        if (
            state.executionTimer
        ) {

            window.clearInterval(
                state.executionTimer
            );


            state.executionTimer = (
                null
            );
        }


        if (
            state.executionStartedAt
            === null
        ) {

            return;
        }


        const elapsed = (
            performance.now()
            - state.executionStartedAt
        );


        setText(
            "#timeline-duration",
            (
                (
                    elapsed
                    / 1000
                )
                    .toFixed(2)
                + " s"
            )
        );


        state.executionStartedAt = (
            null
        );
    }
        /* ========================================================
       MODAL DE WORKFLOW
       ======================================================== */

    function openWorkflowModal() {

        const modal = (
            $("#workflow-modal")
        );

        if (!modal) {
            return;
        }

        modal.hidden = false;

        document.body.style.overflow = (
            "hidden"
        );


        window.setTimeout(
            () => {

                $("#workflow-prompt")
                    ?.focus();
            },
            50
        );
    }


    function closeWorkflowModal() {

        const modal = (
            $("#workflow-modal")
        );

        if (!modal) {
            return;
        }

        modal.hidden = true;

        document.body.style.overflow = (
            ""
        );
    }


    /* ========================================================
       EJECUTAR WORKFLOW REAL
       ======================================================== */

    async function runWorkflow(
        prompt,
        workflow
    ) {

        const cleanPrompt = (
            String(
                prompt || ""
            ).trim()
        );


        const cleanWorkflow = (
            String(
                workflow || ""
            ).trim()
        );


        if (!cleanPrompt) {

            throw new Error(
                "El objetivo del workflow estÃ¡ vacÃ­o."
            );
        }


        if (!cleanWorkflow) {

            throw new Error(
                "No se seleccionÃ³ un workflow."
            );
        }


        state.workflowRunning = true;

        state.currentWorkflow = (
            cleanWorkflow
        );

        state.finalOutput = null;
        state.stepOutputs = {};


        resetExecutionVisuals();

        startExecutionClock();


        updateNode(
            "Executive Agent",
            "RUNNING"
        );


        selectAgent(
            "Executive Agent"
        );


        setText(
            "#metric-running",
            "1"
        );


        appendConsole(
            (
                `Workflow "${cleanWorkflow}" iniciado.`
            ),
            "info"
        );


        addTimelineEvent(
            "workflow-started",
            "Executive Agent",
            "RUNNING",
            cleanWorkflow
        );


        try {

            const payload = (
                await fetchJson(
                    CONFIG.workflowEndpoint,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body: JSON.stringify({
                            prompt: cleanPrompt,
                            workflow: cleanWorkflow,
                        }),
                    }
                )
            );


            state.workflowRunning = false;

            const workflowResult = (
                payload?.result
                ?? payload
                ?? {}
            );

            state.finalOutput = (
                workflowResult?.final_output?.output
                ?? workflowResult?.final_output
                ?? workflowResult?.output
                ?? payload?.final_output?.output
                ?? payload?.final_output
                ?? null
            );

            state.stepOutputs = (
                normalizeStepOutputs(
                    workflowResult?.completed_steps
                    ?? workflowResult?.steps
                    ?? workflowResult?.final_output?.completed_steps
                    ?? payload?.completed_steps
                    ?? []
                )
            );


            updateNode(
                "Executive Agent",
                "COMPLETED"
            );


            updateNode(
                "Final Output",
                "COMPLETED"
            );


            selectAgent(
                "Final Output"
            );


            setText(
                "#metric-running",
                "0"
            );


            appendConsole(
                "Workflow completado correctamente.",
                "success"
            );


            addTimelineEvent(
                "workflow-finished",
                "Final Output",
                "COMPLETED",
                cleanWorkflow
            );


            return payload;

        } catch (error) {

            state.workflowRunning = false;


            updateNode(
                "Executive Agent",
                "FAILED"
            );


            updateNode(
                "Final Output",
                "FAILED"
            );


            setText(
                "#metric-running",
                "0"
            );


            const currentErrors = (
                Number(
                    state.metrics.errors
                    || 0
                )
                + 1
            );


            state.metrics.errors = (
                currentErrors
            );


            setText(
                "#metric-errors",
                currentErrors
            );


            appendConsole(
                (
                    "Error al ejecutar workflow: "
                    + error.message
                ),
                "error"
            );


            addTimelineEvent(
                "workflow-failed",
                "Final Output",
                "FAILED",
                error.message
            );


            throw error;

        } finally {

            stopExecutionClock();


            await refreshStatus({
                silent: true,
            }).catch(
                () => {}
            );
        }
    }


    /* ========================================================
       FORMULARIO DE WORKFLOW
       ======================================================== */

    async function submitWorkflowForm(
        event
    ) {

        event.preventDefault();


        const prompt = (
            $("#workflow-prompt")
                ?.value
                .trim()
            || ""
        );


        const workflow = (
            $("#workflow-name")
                ?.value
            || ""
        );


        if (!prompt) {

            appendConsole(
                (
                    "El objetivo del workflow "
                    + "estÃ¡ vacÃ­o."
                ),
                "warning"
            );


            $("#workflow-prompt")
                ?.focus();


            return;
        }


        const button = (
            $("#execute-workflow")
        );


        if (button) {

            button.disabled = true;

            button.textContent = (
                "Executing..."
            );
        }


        try {

            closeWorkflowModal();


            await runWorkflow(
                prompt,
                workflow
            );


            $("#workflow-form")
                ?.reset();

        } catch {

            /*
            runWorkflow ya registra
            el error en Live Console.
            */

        } finally {

            if (button) {

                button.disabled = false;

                button.textContent = (
                    "Execute"
                );
            }
        }
    }


    /* ========================================================
       EVENTO DIRECTO DEL BOTÃ“N EXECUTE
       ======================================================== */

    async function executeWorkflowFromButton() {

        const form = (
            $("#workflow-form")
        );


        if (!form) {

            appendConsole(
                "No se encontrÃ³ workflow-form.",
                "error"
            );

            return;
        }


        const syntheticEvent = {
            preventDefault() {},
        };


        await submitWorkflowForm(
            syntheticEvent
        );
    }


    /* ========================================================
       NAVEGACIÃ“N
       ======================================================== */

    function bindNavigationEvents() {

        $$(".nav-item")
            .forEach(
                (item) => {

                    item.addEventListener(
                        "click",
                        () => {

                            activateView(
                                item.dataset.section
                            );
                        }
                    );
                }
            );
    }


    /* ========================================================
       CANVAS
       ======================================================== */

    function bindCanvasEvents() {

        const canvas = (
            $("#workflow-canvas")
        );


        if (!canvas) {
            return;
        }


        canvas.addEventListener(
            "click",
            (event) => {

                const node = (
                    event.target.closest(
                        ".workflow-node"
                    )
                );


                if (
                    !node
                    || !node.dataset.agent
                ) {

                    return;
                }


                selectAgent(
                    node.dataset.agent
                );
            }
        );
    }


    /* ========================================================
       CONTROLES DE WORKFLOW
       ======================================================== */

    function bindWorkflowControls() {

        $("#workflow-zoom-in")
            ?.addEventListener(
                "click",
                () => {

                    setWorkflowZoom(
                        state.workflowZoom
                        + 0.1
                    );
                }
            );


        $("#workflow-zoom-out")
            ?.addEventListener(
                "click",
                () => {

                    setWorkflowZoom(
                        state.workflowZoom
                        - 0.1
                    );
                }
            );


        $("#workflow-reset")
            ?.addEventListener(
                "click",
                () => {

                    setWorkflowZoom(
                        1
                    );


                    resetExecutionVisuals();


                    appendConsole(
                        "Workflow visual reiniciado.",
                        "info"
                    );
                }
            );
    }


    /* ========================================================
       EVENTOS DEL MODAL
       ======================================================== */

    function bindModalEvents() {

        $("#run-workflow")
            ?.addEventListener(
                "click",
                openWorkflowModal
            );


        $("#close-workflow-modal")
            ?.addEventListener(
                "click",
                closeWorkflowModal
            );


        $("#cancel-workflow")
            ?.addEventListener(
                "click",
                closeWorkflowModal
            );


        $("#workflow-modal")
            ?.addEventListener(
                "click",
                (event) => {

                    if (
                        event.target.id
                        === "workflow-modal"
                    ) {

                        closeWorkflowModal();
                    }
                }
            );


        $("#workflow-form")
            ?.addEventListener(
                "submit",
                submitWorkflowForm
            );


        $("#execute-workflow")
            ?.addEventListener(
                "click",
                executeWorkflowFromButton
            );


        document.addEventListener(
            "keydown",
            (event) => {

                if (
                    event.key
                    === "Escape"
                ) {

                    closeWorkflowModal();
                }
            }
        );
    }


    /* ========================================================
       CONTROLES GENERALES
       ======================================================== */

    function bindStudioControls() {

        $("#refresh-studio")
            ?.addEventListener(
                "click",
                () => {

                    refreshStatus()
                        .catch(
                            () => {}
                        );
                }
            );


        $("#clear-console")
            ?.addEventListener(
                "click",
                clearConsole
            );


        $("#open-agent-details")
            ?.addEventListener(
                "click",
                openSelectedAgentDetails
            );
    }


    /* ========================================================
       BIND GENERAL
       ======================================================== */

    function bindEvents() {

        bindNavigationEvents();

        bindCanvasEvents();

        bindWorkflowControls();

        bindModalEvents();

        bindStudioControls();
    }


    /* ========================================================
       MÃ‰TRICAS INICIALES
       ======================================================== */

    function initializeMetrics() {

        setText(
            "#metric-organizations",
            "-"
        );


        setText(
            "#metric-departments",
            "-"
        );


        setText(
            "#metric-agents",
            "-"
        );


        setText(
            "#metric-workflows",
            "-"
        );


        setText(
            "#metric-running",
            "0"
        );


        setText(
            "#metric-errors",
            "0"
        );
    }


    /* ========================================================
       CONSOLA INICIAL
       ======================================================== */

    function initializeConsole() {

        appendConsole(
            "Atlas Studio V2 inicializado.",
            "success"
        );


        appendConsole(
            (
                "Esperando estado real "
                + "del Kernel y eventos "
                + "de workflows."
            ),
            "info"
        );
    }
        /* ========================================================
       CIERRE DEL STUDIO
       ======================================================== */

    function shutdownStudio() {

        if (
            state.executionTimer
        ) {

            window.clearInterval(
                state.executionTimer
            );

            state.executionTimer = null;
        }


        disconnectWebSocket();
    }


    /* ========================================================
       INICIALIZACIÃ“N PRINCIPAL
       ======================================================== */

    async function init() {

        bindEvents();


        initializeMetrics();


        initializeConsole();


        activateView(
            "dashboard"
        );


        setConnection(
            false,
            "Connecting"
        );


        appendConsole(
            "Conectando Atlas Studio con el Kernel...",
            "info"
        );


        try {

            await refreshStatus();


        } catch (error) {

            appendConsole(
                (
                    "Error inicializando "
                    + "el estado del Kernel: "
                    + error.message
                ),
                "error"
            );
        }


        connectWebSocket();


        if (
            state.refreshTimer
        ) {

            window.clearInterval(
                state.refreshTimer
            );
        }


        state.refreshTimer = (
            window.setInterval(
                () => {

                    refreshStatus({
                        silent: true,
                    }).catch(
                        () => {}
                    );

                },
                CONFIG.refreshInterval
            )
        );


        window.addEventListener(
            "beforeunload",
            shutdownStudio
        );


        appendConsole(
            "Atlas Studio listo.",
            "success"
        );
    }


    /* ========================================================
       API PÃšBLICA
       ======================================================== */

    return {

        init,

        refreshStatus,

        runWorkflow,

        openWorkflowModal,

        closeWorkflowModal,

        selectAgent,

        activateView,

        appendConsole,

        clearConsole,

        handleWorkflowEvent,

        connectWebSocket,

        disconnectWebSocket,

        resetExecutionVisuals,
    };

})();


/* ============================================================
   ARRANQUE DE ATLAS STUDIO
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        AtlasStudio
            .init()
            .catch(
                (error) => {

                    console.error(
                        "Atlas Studio initialization error:",
                        error
                    );
                }
            );
    }
);
