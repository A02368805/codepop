_ = require 'underscore'
git = require('./index')
Q = require 'q'

git.log()

.then (commits) ->
		# console.log JSON.stringify commits, null, 2
		# fetchDiffs1 commits
		fetchDiffs2 commits
.fail (err) ->
		console.error err

fetchDiffs1 = (commits) ->
	diffs = commits.map (c) -> c.diff()
	Q.all(diffs)
		.then (arr) ->
				arr = _.flatten (arr)
				console.log JSON.stringify arr, null, 2
		.fail (err) ->
				console.error err

fetchDiffs2 = (commits) ->
	commits.diffs()
		.then (arr) ->
				arr = _.flatten (arr)
				console.log JSON.stringify arr, null, 2
		.fail (err) ->
				console.error err
