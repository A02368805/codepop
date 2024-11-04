# git.js

> Simple api to run git commands from nodejs

[![NPM version](https://badge.fury.io/js/git.js.png)](http://badge.fury.io/js/git.js)
[![Build Status](https://drone.io/github.com/sergeyt/git.js/status.png)](https://drone.io/github.com/sergeyt/git.js/latest)
[![Deps Status](https://david-dm.org/sergeyt/git.js.png)](https://david-dm.org/sergeyt/git.js)

[![NPM](https://nodei.co/npm/git.js.png?downloads=true&stars=true)](https://nodei.co/npm/git.js/)

## API

> Note: most of git.js functions return [javascript promises](http://promises-aplus.github.io/promises-spec/).

First you need to call ```require('git')``` to start using git.js API as in example below:

```javascript
var dir = __dirname; // dir with .git repository
var git = require('git')(dir);
```

Next you could call any of the following functions.

### log command

Use log command to fetch array of commits. Example:

```javascript
git.log().then(function(commits){
	commits.forEach(function(commit){
		console.log(commit.id); // sha-hash
		console.log(commit.author.name);
		console.log(commit.author.email);
		console.log(commit.date);
		console.log(commit.message);
	});
});
```

### status command

Use status command to fetch array of changed files to be committed to git database. Example:

```javascript
git.status().then(function(files){
	files.forEach(function(file){
		console.log(file.status);
		console.log(file.path);
	});
});
```

### diff command

Use diff command to fetch diffs for given files. Example:

```javascript
var files = []; // list of file pathes to get diffs for, all changed files when this list is empty or omitted
git.diff(files).then(function(files){
	files.forEach(function(file){
		console.log(file.from); // path to file from working directory
		console.log(file.lines); // modified lines
		console.log(file.deletions); // number of deletions
		console.log(file.additions); // number of additions
	});
});
```

### other functions

All undocumented functions could be found in the source code.

## TODO

* cover more commands
* unit tests
