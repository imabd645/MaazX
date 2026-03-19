import * as vscode from 'vscode';
import { MaazxProvider } from './MaazxProvider';

export function activate(context: vscode.ExtensionContext) {
    console.log('MaazX Extension is now active!');

    const provider = new MaazxProvider(context.extensionUri);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(MaazxProvider.viewType, provider)
    );
}

export function deactivate() { }
