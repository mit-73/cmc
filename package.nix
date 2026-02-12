{
  lib,
  buildPythonApplication,
  setuptools,
  wheel,
  pyyaml,
}:
let
  buildsystem = "pyproject";
  pyproject = builtins.fromTOML (builtins.readFile ./${buildsystem}.toml);
  project = pyproject.project;
  name = project.name;
in
buildPythonApplication {
  inherit (project) version;
  pname = name;
  src = ./.;
  ${buildsystem} = true;

  postUnpack = ''
    mkdir -p ${name}-wrapper
    mv $sourceRoot ${name}-wrapper/${name}
    sourceRoot=${name}-wrapper/${name}
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
    mainProgram = name;
    homepage = "https://github.com/mit-73/${name}";
  };
}
