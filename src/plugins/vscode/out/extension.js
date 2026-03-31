"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const cp = __importStar(require("child_process"));
const node_1 = require("vscode-languageclient/node");
let client;
let statusItem;
const output = vscode.window.createOutputChannel("physlint");
const PHYSLINT_PKG = "physlint[lsp] @ git+https://github.com/Darsh-A/physlint.git";
function isWindows() {
    return process.platform === "win32";
}
function venvPython(venvDir) {
    return isWindows()
        ? path.join(venvDir, "Scripts", "python.exe")
        : path.join(venvDir, "bin", "python");
}
function run(cmd, args) {
    return new Promise((resolve) => {
        const proc = cp.spawn(cmd, args, { shell: isWindows() });
        let stdout = "";
        let stderr = "";
        proc.stdout.on("data", (d) => (stdout += d));
        proc.stderr.on("data", (d) => (stderr += d));
        proc.on("close", (code) => resolve({ code: code ?? 1, stdout, stderr }));
    });
}
function findSystemPython() {
    const config = vscode.workspace.getConfiguration("physlint");
    const explicit = config.get("pythonPath");
    if (explicit && explicit !== "python" && explicit !== "auto") {
        return explicit;
    }
    const pyConfig = vscode.workspace.getConfiguration("python");
    const pyInterp = pyConfig.get("defaultInterpreterPath");
    if (pyInterp && pyInterp !== "python") {
        return pyInterp;
    }
    const ws = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (ws) {
        for (const dir of [".venv", "venv"]) {
            const candidate = venvPython(path.join(ws, dir));
            if (fs.existsSync(candidate)) {
                return candidate;
            }
        }
    }
    return isWindows() ? "python" : "python3";
}
function getPrivateVenvDir(context) {
    return path.join(context.globalStorageUri.fsPath, "venv");
}
async function ensurePhyslint(context) {
    const venvDir = getPrivateVenvDir(context);
    const python = venvPython(venvDir);
    if (fs.existsSync(python)) {
        output.appendLine(`private venv exists: ${venvDir}`);
        return python;
    }
    output.appendLine("setting up physlint for the first time...");
    const sysPython = findSystemPython();
    output.appendLine(`system python: ${sysPython}`);
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "physlint",
        cancellable: false,
    }, async (progress) => {
        progress.report({ message: "creating environment..." });
        fs.mkdirSync(path.dirname(venvDir), { recursive: true });
        const venvResult = await run(sysPython, ["-m", "venv", venvDir]);
        if (venvResult.code !== 0) {
            output.appendLine(`venv creation failed: ${venvResult.stderr}`);
            throw new Error(`failed to create venv: ${venvResult.stderr}`);
        }
        output.appendLine("venv created");
        progress.report({ message: "installing physlint (this may take a minute)..." });
        const pipResult = await run(python, ["-m", "pip", "install", "--upgrade", PHYSLINT_PKG]);
        output.appendLine(pipResult.stdout);
        if (pipResult.code !== 0) {
            output.appendLine(`pip install failed: ${pipResult.stderr}`);
            throw new Error(`pip install failed: ${pipResult.stderr}`);
        }
        output.appendLine("physlint installed");
    });
    return python;
}
async function startServer(context) {
    let pythonPath;
    try {
        pythonPath = await ensurePhyslint(context);
    }
    catch (err) {
        statusItem.text = "$(error) physlint";
        statusItem.tooltip = "setup failed — click for details";
        statusItem.command = "physlint.showOutput";
        output.appendLine(`setup failed: ${err.message}`);
        vscode.window.showErrorMessage(`physlint setup failed. Make sure Python 3.11+ is installed.\n\n${err.message}`, "Show Output").then((a) => { if (a) {
            output.show();
        } });
        return;
    }
    output.appendLine(`starting LSP with: ${pythonPath}`);
    const serverOptions = {
        command: pythonPath,
        args: ["-m", "physlint.lsp"],
        options: { cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath },
    };
    const clientOptions = {
        documentSelector: [{ scheme: "file", language: "python" }],
        outputChannel: output,
    };
    client = new node_1.LanguageClient("physlint", "physlint", serverOptions, clientOptions);
    try {
        await client.start();
        statusItem.text = "$(check) physlint";
        statusItem.tooltip = `physlint running`;
        output.appendLine("LSP server started");
    }
    catch (err) {
        statusItem.text = "$(error) physlint";
        statusItem.tooltip = "server failed — click for details";
        statusItem.command = "physlint.showOutput";
        output.appendLine(`server failed: ${err.message}`);
        vscode.window.showErrorMessage(`physlint server failed to start: ${err.message}`, "Show Output")
            .then((a) => { if (a) {
            output.show();
        } });
    }
}
function activate(context) {
    const config = vscode.workspace.getConfiguration("physlint");
    if (!config.get("enable", true)) {
        return;
    }
    statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusItem.text = "$(loading~spin) physlint";
    statusItem.tooltip = "physlint starting...";
    statusItem.show();
    context.subscriptions.push(statusItem);
    context.subscriptions.push(vscode.commands.registerCommand("physlint.restart", async () => {
        output.appendLine("restarting...");
        if (client) {
            await client.stop();
            client = undefined;
        }
        await startServer(context);
    }), vscode.commands.registerCommand("physlint.reinstall", async () => {
        output.appendLine("reinstalling physlint...");
        if (client) {
            await client.stop();
            client = undefined;
        }
        const venvDir = getPrivateVenvDir(context);
        if (fs.existsSync(venvDir)) {
            fs.rmSync(venvDir, { recursive: true, force: true });
            output.appendLine("removed old venv");
        }
        await startServer(context);
    }), vscode.commands.registerCommand("physlint.showOutput", () => {
        output.show();
    }));
    startServer(context);
}
function deactivate() {
    return client?.stop();
}
//# sourceMappingURL=extension.js.map