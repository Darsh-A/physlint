import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import * as cp from "child_process";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
} from "vscode-languageclient/node";

let client: LanguageClient | undefined;
let statusItem: vscode.StatusBarItem;
const output = vscode.window.createOutputChannel("physlint");

const PHYSLINT_PKG = "physlint[lsp] @ git+https://github.com/Darsh-A/physlint.git";

function isWindows(): boolean {
  return process.platform === "win32";
}

function venvPython(venvDir: string): string {
  return isWindows()
    ? path.join(venvDir, "Scripts", "python.exe")
    : path.join(venvDir, "bin", "python");
}

function run(cmd: string, args: string[]): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const proc = cp.spawn(cmd, args, { shell: isWindows() });
    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d));
    proc.stderr.on("data", (d) => (stderr += d));
    proc.on("close", (code) => resolve({ code: code ?? 1, stdout, stderr }));
  });
}

function findSystemPython(): string {
  const config = vscode.workspace.getConfiguration("physlint");
  const explicit = config.get<string>("pythonPath");
  if (explicit && explicit !== "python" && explicit !== "auto") {
    return explicit;
  }

  const pyConfig = vscode.workspace.getConfiguration("python");
  const pyInterp = pyConfig.get<string>("defaultInterpreterPath");
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

function getPrivateVenvDir(context: vscode.ExtensionContext): string {
  return path.join(context.globalStorageUri.fsPath, "venv");
}

async function ensurePhyslint(context: vscode.ExtensionContext): Promise<string> {
  const venvDir = getPrivateVenvDir(context);
  const python = venvPython(venvDir);

  if (fs.existsSync(python)) {
    output.appendLine(`private venv exists: ${venvDir}`);
    return python;
  }

  output.appendLine("setting up physlint for the first time...");

  const sysPython = findSystemPython();
  output.appendLine(`system python: ${sysPython}`);

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "physlint",
      cancellable: false,
    },
    async (progress) => {
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
    }
  );

  return python;
}

async function startServer(context: vscode.ExtensionContext) {
  let pythonPath: string;

  try {
    pythonPath = await ensurePhyslint(context);
  } catch (err: any) {
    statusItem.text = "$(error) physlint";
    statusItem.tooltip = "setup failed — click for details";
    statusItem.command = "physlint.showOutput";
    output.appendLine(`setup failed: ${err.message}`);
    vscode.window.showErrorMessage(
      `physlint setup failed. Make sure Python 3.11+ is installed.\n\n${err.message}`,
      "Show Output"
    ).then((a) => { if (a) { output.show(); } });
    return;
  }

  output.appendLine(`starting LSP with: ${pythonPath}`);

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
    statusItem.tooltip = `physlint running`;
    output.appendLine("LSP server started");
  } catch (err: any) {
    statusItem.text = "$(error) physlint";
    statusItem.tooltip = "server failed — click for details";
    statusItem.command = "physlint.showOutput";
    output.appendLine(`server failed: ${err.message}`);
    vscode.window.showErrorMessage(`physlint server failed to start: ${err.message}`, "Show Output")
      .then((a) => { if (a) { output.show(); } });
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
    vscode.commands.registerCommand("physlint.reinstall", async () => {
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
