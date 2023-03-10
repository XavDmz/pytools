---
hide:
  - navigation
---

<div id="version_menu">
  <b>1.2.1</b>
  <a href="../">Documentation générale</a>
  <a href="../CHANGELOG/">Changements</a>
</div>

# Changements

## Summary

Ajout de l'outil make-layer et suivi des recommandations PyPA pour la gestion du projet.

## Changelog

### [Added]

* Outil MAKE-LAYER : génère un descripteur de couche compatible avec le serveur à partir des pyramides de données à utiliser
* Ajout de la publication PyPI dans la CI GitHub 

### [Changed]

* Renommage pour plus de cohérence avec les pratiques :
    * Le module rok4 est renommé : rok4lib -> rok4
    * Le module d'outil est renommé : rok4tools -> rok4_tools. Le package a le nom rok4-tools
    * Le script make-layer.py -> make_layer.py
* Passage de la configuration du projet dans le fichier `pyproject.toml`

<!-- 
### [Added]

### [Changed]

### [Deprecated]

### [Removed]

### [Fixed]

### [Security] 
-->