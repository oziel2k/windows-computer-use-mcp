/**
 * Declared mock-until-onboarded sample content (docs/ONBOARDING.md § Declared doubles).
 *
 * Shown ONLY while the backend is unreachable. Every surface carries a MOCK
 * badge (data-testid="mock-badge") plus the page banner
 * (data-testid="mock-data-banner"). All content clears the moment health
 * reports reachable — there is no toggle to keep mocks.
 */

export const MOCK_ACTORS = ["Joe Mocky", "Sandra Mockinger"] as const;

export const MOCK_HOST = {
	cpu_percent: 23.5,
	memory_percent: 41.2,
	memory_available_gb: 18.4,
	memory_total_gb: 32.0,
	disk_percent: 57.8,
	disk_path: "C:",
	disk_used_gb: 289.1,
	disk_total_gb: 500.0,
	window_count: 7,
} as const;

export const MOCK_WINDOWS = [
	{ title: "[MOCK] Notepad — Joe Mocky notes", app: "notepad.exe" },
	{ title: "[MOCK] Settings — Sandra Mockinger", app: "SystemSettings.exe" },
] as const;
