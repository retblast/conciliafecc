{
  description = "Entorno de desarrollo de ConciliaFECC";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { nixpkgs, ... }: {
    devShells = nixpkgs.lib.genAttrs [ "x86_64-linux" "aarch64-linux" ] (system:
      let pkgs = nixpkgs.legacyPackages.${system};
      in {
        default = pkgs.mkShell {
          packages = [ pkgs.python314 pkgs.uv ];
          UV_PYTHON = "${pkgs.python314}/bin/python3";
          UV_PYTHON_DOWNLOADS = "never";
          UV_PROJECT_ENVIRONMENT = ".venv-nix";
        };
      });
  };
}
