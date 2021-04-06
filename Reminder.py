class Reminder:
    def __init__(self, content, remindType, channelID, serverID, dateTime, isActive=True):
        self.content = content
        self.type = remindType
        self.channelID = channelID
        self.serverID = serverID
        self.dateTime = dateTime
        self.isActive = isActive

