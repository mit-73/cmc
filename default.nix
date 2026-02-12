{ pkgs, ... }:
let
  python = pkgs.python3Packages;
in
{
  flake = rec {
    packages = rec {
      minimal = python.callPackage ./package.nix { };

      dart = minimal.overridePythonAttrs (old: {
        dependencies =
          old.dependencies
          ++ (with python; [
            tree-sitter
            tree-sitter-grammars.tree-sitter-dart
          ]);
      });
    };

    shell = builtins.attrValues packages ++ [
      (python.python.withPackages (_: packages.dart.dependencies))
    ];
  };
}
