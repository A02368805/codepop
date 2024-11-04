fs = require 'fs'
path = require 'path'
dir = path.join __dirname, 'tmp'
fs.mkdirSync dir

git = require('../index')(dir)

git.init()
	.then	->
			console.log 'done'
	.fail (err) ->
			console.error err
