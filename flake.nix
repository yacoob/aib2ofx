{
  description = "Download data from aib.ie in OFX format";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = {nixpkgs, ...}: let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
    python = pkgs.python313;
  in {
    devShells.${system}.default = pkgs.mkShell {
      packages = [
        python
        pkgs.uv
        pkgs.watchexec
      ];

      env = {
        # uv resolves the venv against this interpreter instead of fetching
        # its own python-build-standalone build, which would need nix-ld to run.
        UV_PYTHON = python.interpreter;
        UV_PYTHON_DOWNLOADS = "never";
      };
    };
  };
}
