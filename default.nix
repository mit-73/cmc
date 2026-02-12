{ pkgs, ... }:
{
  flake.packages = rec {
    minimal = pkgs.python3Packages.callPackage ./package.nix { };

    dart = minimal.overridePythonAttrs (old: {
      dependencies =
        old.dependencies
        ++ (with pkgs.python3Packages; [
          tree-sitter
          tree-sitter-grammars.tree-sitter-dart
        ]);
    });
  };
}
