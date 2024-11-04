fs = require 'fs'
path = require 'path'
tmp = path.join(__dirname, 'tmp')
fs.mkdirSync tmp unless fs.existsSync tmp
git = require('../index')(tmp)

git.clone('https://github.com/sergeyt/git.js')
	.then ->
			console.log 'done'
	.fail (err) ->
			console.error err
