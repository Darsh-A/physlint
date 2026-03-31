import * as vscode from "vscode";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
} from "vscode-languageclient/node";

let client: LanguageClient | undefined;

export function activate(context: vscode.ExtensionContext) {
  const config = vscode.workspace.getConfiguration("physlint");
  if (!config.get<boolean>("enable", true)) {
    return;
  }

  const pythonPath = config.get<string>("pythonPath", "python");

  const serverOptions: ServerOptions = {
    command: pythonPath,
    args: ["-m", "physlint.lsp"],
    options: { cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath },
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: "file", language: "python" }],
  };

  client = new LanguageClient(
    "physlint",
    "physlint",
    serverOptions,
    clientOptions
  );

  client.start();
  context.subscriptions.push({
    dispose: () => {
      client?.stop();
    },
  });
}

export function deactivate(): Thenable<void> | undefined {
  return client?.stop();
}
