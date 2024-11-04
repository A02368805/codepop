git = require './index'

git.status()
	.then (files) ->
			console.log JSON.stringify files, null, 2
	.fail (err) ->
			console.error err
