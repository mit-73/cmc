{
  lib,
  buildPythonApplication,
  setuptools,
  wheel,
  pyyaml,
}:

buildPythonApplication {
  pname = "cmc";
  version = "1.0.0";

  src = ./.;
  pyproject = true;

  postUnpack = ''
    mkdir -p cmc-wrapper
    mv $sourceRoot cmc-wrapper/cmc
    sourceRoot=cmc-wrapper/cmc
  '';

  build-system = [
    setuptools
    wheel
  ];

  dependencies = [
    pyyaml
  ];

  doCheck = false;

  meta = {
    description = "Code quality metrics collector for Dart monorepos";
    license = lib.licenses.mit;
    mainProgram = "cmc";
    homepage = "https://github.com/mit-73/cmc";
  };
}
