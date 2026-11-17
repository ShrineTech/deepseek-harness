# mkhome-sando.py <home> <provider-id> <model-id> <inside-port> <ctx>
# An isolated Sando HOME with exactly one provider: the local model behind the box relay (no other providers, no keys).
import json, pathlib, sys
home, pid, mid, port, ctx = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
cfg = {"schemaVersion": 1, "config": {
    "providerOrder": [pid],
    "providerConfigRules": {"providerRules": [{"providerId": pid, "enabled": True, "config": {
        "group": "standard-personal", "access": {"type": "api-key", "apiKey": "local-no-key"},
        "api": {"type": "openai-chat-completions", "baseUrl": f"http://127.0.0.1:{port}/v1"},
        "personalModelIds": [mid], "modelOrder": [mid]}}]},
    "modelConfigRules": {"providerModelRules": [], "manualProviderModelRules": [{"providerId": pid, "modelId": mid, "config": {
        "enabled": True,
        "properties": {"contextWindow": ctx, "supportsJsonSchemaOutput": False, "supportsNativeWebSearch": False,
                       "supportsMidConversationSystem": False,
                       "inputFormat": {"supportsImage": False, "supportsVideo": False, "supportsPdf": False}},
        "optionSpecs": {"reasoningLevel": {"values": ["disabled", "enabled"], "map": "{}"}, "maxOutputTokens": {"max": 8192}}}}]},
    "defaultModelSelection": {"providerId": pid, "modelId": mid}}}
h = pathlib.Path(home)
(h / ".zcode/v2").mkdir(parents=True, exist_ok=True)
(h / ".zcode/cli").mkdir(parents=True, exist_ok=True)
json.dump(cfg, open(h / ".zcode/v2/provider_config.json", "w"), indent=2)
json.dump({"permission": {"mode": "yolo"}, "logging": {"level": "info"}}, open(h / ".zcode/cli/config.json", "w"))
