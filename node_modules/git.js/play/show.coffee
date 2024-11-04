git = require('./index')

git.show.diff('bce321f68e78c07b39a2f194811ab041a91962bb')
	.then (diff) ->
			console.log JSON.stringify diff, null, 2
	.fail (err) ->
			console.error err
