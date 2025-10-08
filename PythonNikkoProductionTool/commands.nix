{
  pkgs ? import <nixpkgs> { },
  prefix ? "npt",
}:
let

  commands = pkgs.lib.fix (
    self:
    pkgs.lib.mapAttrs pkgs.writeShellScript {
      welcome = ''
        ${pkgs.lib.getExe pkgs.figlet} 'Nikko Production Tool Dev Shell' | ${pkgs.lib.getExe pkgs.lolcat}
        echo 'press ${prefix}-<TAB><TAB> to see all the commands'
      '';

      launchAppLinux = ''
        export QT_QPA_PLATFORM=wayland && cd /home/jackd/repos/NikkoProductionTool/src && python main.py
      '';
    }
  );
in
pkgs.symlinkJoin rec {
  name = prefix;
  passthru.set = commands;
  passthru.bin = pkgs.lib.mapAttrs (
    name: command:
    pkgs.runCommand "${prefix}-${name}" { } ''
      mkdir -p $out/bin
      ln -sf ${command} $out/bin/${if name == "default" then prefix else prefix + "-" + name}
    ''
  ) commands;
  paths = pkgs.lib.attrValues passthru.bin;
}
