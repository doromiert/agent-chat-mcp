{ lib, python3, stdenvNoCC, makeWrapper }:
let python = python3.withPackages (ps: [ ps.mcp ]);
in stdenvNoCC.mkDerivation {
  pname = "agent-chat-mcp";
  version = "0.1.0";
  src = lib.cleanSource ./.;
  nativeBuildInputs = [ makeWrapper ];
  dontBuild = true;
  doCheck = true;
  checkPhase = ''
    ${python}/bin/python3 -m unittest discover -s tests -v
  '';
  installPhase = ''
    mkdir -p "$out/bin" "$out/libexec/agent-chat-mcp" "$out/share/agent-chat-mcp"
    cp agent_chat.py "$out/libexec/agent-chat-mcp/"
    cp default-instructions.md "$out/share/agent-chat-mcp/AGENTS.md"
    makeWrapper ${python}/bin/python3 "$out/bin/agent-chat-mcp" \
      --add-flags "$out/libexec/agent-chat-mcp/agent_chat.py"
  '';
  meta = {
    description = "Local durable group chat for independent coding agents over MCP";
    license = lib.licenses.mit;
    platforms = lib.platforms.linux;
    mainProgram = "agent-chat-mcp";
  };
}
