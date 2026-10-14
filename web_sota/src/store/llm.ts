import { useSyncExternalStore } from "react";
import { apiPath } from "@/lib/api";

export interface LlmProvider {
	id: string;
	label: string;
	base_url: string;
	models: string[];
	needs_key: boolean;
}

export interface DiscoverProvider {
	id: string;
	label: string;
	base_url: string;
	detected: boolean;
	models: string[];
	needs_key: boolean;
}

interface LlmStoreState {
	providers: LlmProvider[];
	selectedProvider: string;
	selectedModel: string;
	discover: DiscoverProvider[];
	gpuPresent: boolean | null;
	discoverCheckedAt: string | null;
	onboardingConfigured: boolean | null;
}

const LS_PROVIDER = "pywinauto-llm-provider";
const LS_MODEL = "pywinauto-llm-model";

let state: LlmStoreState = {
	providers: [],
	selectedProvider:
		typeof localStorage !== "undefined"
			? localStorage.getItem(LS_PROVIDER) || "ollama"
			: "ollama",
	selectedModel:
		typeof localStorage !== "undefined"
			? localStorage.getItem(LS_MODEL) || ""
			: "",
	discover: [],
	gpuPresent: null,
	discoverCheckedAt: null,
	onboardingConfigured: null,
};

const listeners = new Set<() => void>();
function emit() {
	for (const l of listeners) l();
}
function subscribe(fn: () => void) {
	listeners.add(fn);
	return () => {
		listeners.delete(fn);
	};
}

export function setProviders(providers: LlmProvider[]) {
	state = { ...state, providers };
	emit();
}

export function selectLlm(provider: string, model: string) {
	try {
		localStorage.setItem(LS_PROVIDER, provider);
		localStorage.setItem(LS_MODEL, model);
	} catch {
		// private mode — store stays in memory
	}
	state = { ...state, selectedProvider: provider, selectedModel: model };
	emit();
}

export function setDiscover(
	providers: DiscoverProvider[],
	gpuPresent: boolean,
) {
	state = {
		...state,
		discover: providers,
		gpuPresent,
		discoverCheckedAt: new Date().toISOString(),
	};
	emit();
}

export async function refreshDiscover(): Promise<void> {
	try {
		const r = await fetch(apiPath("/api/v1/llm/discover"));
		const j = (await r.json()) as {
			providers?: DiscoverProvider[];
			gpu_present?: boolean;
		};
		if (r.ok && Array.isArray(j.providers)) {
			setDiscover(j.providers, Boolean(j.gpu_present));
		}
	} catch {
		// backend unreachable — leave previous discover state
	}
}

export function setOnboardingConfigured(configured: boolean) {
	state = { ...state, onboardingConfigured: configured };
	emit();
}

export function useLlmStore(): LlmStoreState {
	return useSyncExternalStore(
		subscribe,
		() => state,
		() => state,
	);
}
