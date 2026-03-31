import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
} from "vscode-languageclient/node";

let client: LanguageClient | undefined;
let statusItem: vscode.StatusBarItem;
const output = vscode.window.createOutputChannel("physlint");

function findPython(): string {
  const config = vscode.workspace.getConfiguration("physlint");
  const explicit = config.get<string>("pythonPath");
  if (explicit && explicit !== "python") {
    return explicit;
  }

  // try the ms-python extension's selected interpreter
  const pyConfig = vscode.workspace.getConfiguration("python");
  const pyInterp = pyConfig.get<string>("defaultInterpreterPath");
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

async function startServer(context: vscode.ExtensionContext) {
  const pythonPath = findPython();
  output.appendLine(`using python: ${pythonPath}`);

  const serverOptions: ServerOptions = {
    command: pythonPath,
    args: ["-m", "physlint.lsp"],
    options: { cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath },
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: "file", language: "python" }],
    outputChannel: output,
  };

  client = new LanguageClient("physlint", "physlint", serverOptions, clientOptions);

  try {
    await client.start();
    statusItem.text = "$(check) physlint";
    statusItem.tooltip = `physlint running (${pythonPath})`;
    output.appendLine("LSP server started");
  } catch (err: any) {
    statusItem.text = "$(error) physlint";
    statusItem.tooltip = "physlint failed to start — click for details";
    statusItem.command = "physlint.showOutput";
    output.appendLine(`failed to start: ${err.message}`);

    const msg = `physlint LSP server failed to start. Make sure physlint[lsp] is installed in your Python environment:\n\npython -m pip install "physlint[lsp]"`;
    const action = await vscode.window.showErrorMessage(msg, "Show Output", "Open Settings");
    if (action === "Show Output") {
      output.show();
    } else if (action === "Open Settings") {
      vscode.commands.executeCommand("workbench.action.openSettings", "physlint.pythonPath");
    }
  }
}

export function activate(context: vscode.ExtensionContext) {
  const config = vscode.workspace.getConfiguration("physlint");
  if (!config.get<boolean>("enable", true)) {
    return;
  }

  statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
  statusItem.text = "$(loading~spin) physlint";
  statusItem.tooltip = "physlint starting...";
  statusItem.show();
  context.subscriptions.push(statusItem);

  context.subscriptions.push(
    vscode.commands.registerCommand("physlint.restart", async () => {
      output.appendLine("restarting...");
      if (client) {
        await client.stop();
        client = undefined;
      }
      await startServer(context);
    }),
    vscode.commands.registerCommand("physlint.showOutput", () => {
      output.show();
    })
  );

  startServer(context);
}

export function deactivate(): Thenable<void> | undefined {
  return client?.stop();
}
