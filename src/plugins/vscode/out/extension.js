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
const node_1 = require("vscode-languageclient/node");
let client;
let statusItem;
const output = vscode.window.createOutputChannel("physlint");
function findPython() {
    const config = vscode.workspace.getConfiguration("physlint");
    const explicit = config.get("pythonPath");
    if (explicit && explicit !== "python") {
        return explicit;
    }
    // try the ms-python extension's selected interpreter
    const pyConfig = vscode.workspace.getConfiguration("python");
    const pyInterp = pyConfig.get("defaultInterpreterPath");
    if (pyInterp && pyInterp !== "python") {
        return pyInterp;
    }
    // look for a local venv in the workspace
    const ws = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (ws) {
        for (const dir of [".venv", "venv"]) {
            const candidate = path.join(ws, dir, "bin", "python");
            if (fs.existsSync(candidate)) {
                output.appendLine(`found venv python: ${candidate}`);
                return candidate;
            }
        }
    }
    return "python";
}
async function startServer(context) {
    const pythonPath = findPython();
    output.appendLine(`using python: ${pythonPath}`);
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
        statusItem.tooltip = `physlint running (${pythonPath})`;
        output.appendLine("LSP server started");
    }
    catch (err) {
        statusItem.text = "$(error) physlint";
        statusItem.tooltip = "physlint failed to start — click for details";
        statusItem.command = "physlint.showOutput";
        output.appendLine(`failed to start: ${err.message}`);
        const msg = `physlint LSP server failed to start. Make sure physlint[lsp] is installed in your Python environment:\n\npython -m pip install "physlint[lsp]"`;
        const action = await vscode.window.showErrorMessage(msg, "Show Output", "Open Settings");
        if (action === "Show Output") {
            output.show();
        }
        else if (action === "Open Settings") {
            vscode.commands.executeCommand("workbench.action.openSettings", "physlint.pythonPath");
        }
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
    }), vscode.commands.registerCommand("physlint.showOutput", () => {
        output.show();
    }));
    startServer(context);
}
function deactivate() {
    return client?.stop();
}
//# sourceMappingURL=extension.js.map